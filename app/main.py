from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import sqlite3, threading, time, cv2, numpy as np, psutil, os, math

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
STORAGE = ROOT / "storage"
SNAPSHOTS = ROOT / "snapshots"
for p in (STORAGE, SNAPSHOTS): p.mkdir(exist_ok=True)
DB = STORAGE / "visionguard.db"

app = FastAPI(title="AI VisionGuard", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

class Settings(BaseModel):
    confidence: float = 0.45
    focal_length: float = 700.0
    unit: str = "m"
    restricted_enabled: bool = True

class CameraWorker:
    def __init__(self):
        self.lock = threading.RLock(); self.cap = None; self.thread = None; self.running = False
        self.frame = None; self.annotated = None; self.detections = []; self.fps = 0.0
        self.settings = Settings(); self.model = None; self.last_event = 0
        self.total_frames = 0; self.started_at = None
        self.object_heights = {"person":1.70,"cat":0.23,"dog":0.60,"horse":1.60,"sheep":0.75,"cow":1.45,"elephant":2.70,"bear":1.00,"zebra":1.30,"giraffe":4.20,"bird":0.12,"car":1.50,"motorcycle":1.10,"bicycle":1.10,"bus":3.20,"truck":3.20}

    def load_model(self):
        if YOLO is None: raise RuntimeError("Ultralytics is not installed. Run start_windows.bat.")
        if self.model is None: self.model = YOLO("yolo11n.pt")

    def start(self, index=0):
        with self.lock:
            if self.running: return True
            self.load_model()
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
            if not cap.isOpened(): cap.release(); raise RuntimeError(f"Cannot open camera index {index}.")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540); cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap = cap; self.running = True; self.started_at = time.time(); self.thread = threading.Thread(target=self.loop, daemon=True); self.thread.start(); return True

    def stop(self):
        with self.lock:
            self.running = False
            t = self.thread
        if t and t.is_alive() and t is not threading.current_thread(): t.join(timeout=3)
        with self.lock:
            if self.cap: self.cap.release(); self.cap = None
            self.thread = None
            self.frame = None; self.annotated = None; self.detections = []; self.fps = 0.0

    def estimate_distance(self, cls, hpx):
        real_h = self.object_heights.get(cls, 1.0)
        if hpx <= 0: return None
        return max(0.1, (real_h * self.settings.focal_length) / hpx)

    def risk(self, cls, distance, cx, frame_w):
        if distance is None: return "LOW", 10
        if cls == "person":
            if distance < 2: return "CRITICAL", 95
            if distance < 5: return "HIGH", 80
            if distance < 10: return "MEDIUM", 55
        elif cls in ("dog","cat","horse","cow","bear","elephant"):
            if distance < 3: return "HIGH", 75
            if distance < 8: return "MEDIUM", 50
        return "LOW", 20

    def loop(self):
        prev = time.time(); frames = 0
        while self.running:
            cap = self.cap
            ret, frame = cap.read() if cap else (False,None)
            if not ret: time.sleep(.05); continue
            now=time.time(); frames += 1
            if now-prev >= 1: self.fps=frames/(now-prev); frames=0; prev=now
            try:
                results = self.model.predict(frame, conf=self.settings.confidence, iou=.5, max_det=30, verbose=False)
                dets=[]; annotated=frame.copy()
                if results and results[0].boxes is not None:
                    names=results[0].names
                    for box in results[0].boxes:
                        cls_id=int(box.cls[0]); cls=str(names[cls_id]).lower(); conf=float(box.conf[0]); x1,y1,x2,y2=map(int,box.xyxy[0])
                        h=y2-y1; dist=self.estimate_distance(cls,h); cx=(x1+x2)//2; risk,score=self.risk(cls,dist,cx,frame.shape[1])
                        d={"id":len(dets)+1,"object":cls,"confidence":round(conf,3),"bbox":[x1,y1,x2,y2],"distance":round(dist,2) if dist else None,"risk":risk,"score":score,"zone":"Restricted" if self.settings.restricted_enabled and cx > frame.shape[1]*.65 else "Safe"}
                        dets.append(d)
                        colors={"CRITICAL":(0,0,255),"HIGH":(0,100,255),"MEDIUM":(0,200,255),"LOW":(0,220,80)}; color=colors[risk]
                        cv2.rectangle(annotated,(x1,y1),(x2,y2),color,2)
                        label=f"{cls} {conf:.0%} | {dist:.1f}m | {risk}" if dist else f"{cls} {conf:.0%} | {risk}"
                        cv2.rectangle(annotated,(x1,max(0,y1-28)),(min(frame.shape[1],x1+len(label)*10+8),y1),color,-1)
                        cv2.putText(annotated,label,(x1+4,max(18,y1-7)),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1,cv2.LINE_AA)
                        if risk in ("CRITICAL","HIGH") and now-self.last_event>2:
                            self.last_event=now; self.save_event(d)
                with self.lock: self.frame=frame; self.annotated=annotated; self.detections=dets; self.total_frames+=1
            except Exception as e:
                cv2.putText(frame,f"AI error: {str(e)[:80]}",(10,30),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,255),2)
                with self.lock: self.frame=frame; self.annotated=frame; self.detections=[]
            time.sleep(.01)

    def save_event(self,d):
        conn=sqlite3.connect(DB); conn.execute("INSERT INTO events(ts,object,confidence,distance,risk,score,zone) VALUES(?,?,?,?,?,?,?)",(datetime.now().isoformat(timespec='seconds'),d['object'],d['confidence'],d['distance'],d['risk'],d['score'],d['zone'])); conn.commit(); conn.close()
        with self.lock:
            if self.annotated is not None: cv2.imwrite(str(SNAPSHOTS/f"event_{int(time.time())}.jpg"),self.annotated)

worker=CameraWorker()

def init_db():
    c=sqlite3.connect(DB); c.execute("CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,ts TEXT,object TEXT,confidence REAL,distance REAL,risk TEXT,score INTEGER,zone TEXT)"); c.commit(); c.close()
init_db()

@app.get("/", response_class=HTMLResponse)
def home(): return (STATIC/"index.html").read_text(encoding="utf-8")

@app.post("/api/start")
def start(camera_index:int=0):
    try: worker.start(camera_index); return {"ok":True,"message":"Camera started"}
    except Exception as e: raise HTTPException(500,str(e))

@app.post("/api/stop")
def stop(): worker.stop(); return {"ok":True,"message":"Camera stopped"}

@app.get("/api/status")
def status():
    with worker.lock: ds=list(worker.detections); running=worker.running
    return {"running":running,"fps":round(worker.fps,1),"cpu":round(psutil.cpu_percent(interval=None),1),"memory":round(psutil.virtual_memory().percent,1),"detections":ds,"objects":len(ds),"critical":sum(d['risk'] in ('CRITICAL','HIGH') for d in ds)}

@app.get("/api/events")
def events(limit:int=50):
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; rows=[dict(r) for r in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?",(max(1,min(limit,200)),))]; c.close(); return rows

@app.get("/api/snapshot")
def snapshot():
    with worker.lock: img=None if worker.annotated is None else worker.annotated.copy()
    if img is None: raise HTTPException(409,"Camera is not running")
    path=SNAPSHOTS/f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"; cv2.imwrite(str(path),img); return {"ok":True,"file":path.name}

@app.get("/api/settings")
def get_settings(): return worker.settings.model_dump()

@app.post("/api/settings")
def set_settings(s:Settings):
    s.confidence=max(.1,min(.95,s.confidence)); s.focal_length=max(50,min(5000,s.focal_length)); worker.settings=s; return s.model_dump()

@app.get("/video_feed")
def video_feed():
    def gen():
        while True:
            with worker.lock: img=None if worker.annotated is None else worker.annotated.copy()
            if img is None:
                img = np.zeros((540,960,3),dtype=np.uint8)
                time.sleep(.2)
            ok,buf=cv2.imencode('.jpg',img,[int(cv2.IMWRITE_JPEG_QUALITY),80])
            if ok: yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'+buf.tobytes()+b'\r\n'
            time.sleep(.03)
    return StreamingResponse(gen(),media_type='multipart/x-mixed-replace; boundary=frame')
