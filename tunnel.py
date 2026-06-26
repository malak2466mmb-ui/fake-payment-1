import socket
import threading
import urllib.request
import json

def get_public_ip():
    try:
        with urllib.request.urlopen('https://api.ipify.org?format=json') as response:
            data = json.loads(response.read())
            return data['ip']
    except:
        return None

def create_tunnel(local_port=5000, remote_port=8080):
    public_ip = get_public_ip()
    if public_ip:
        print(f"🌐 Your public IP: {public_ip}")
        print(f"🔗 Try: http://{public_ip}:{remote_port}")
        print(f"⚠️ Note: You need to port forward {remote_port} to {local_port} in your router")
    else:
        print("❌ Could not get public IP")

    # Create simple TCP tunnel
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind(('0.0.0.0', remote_port))
        server.listen(5)
        print(f"✅ Tunnel running on port {remote_port}")
        
        while True:
            client, addr = server.accept()
            print(f"📡 Connection from {addr}")
            
            # Forward to local port
            try:
                local = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                local.connect(('localhost', local_port))
                
                # Start forwarding threads
                def forward(source, destination):
                    while True:
                        data = source.recv(4096)
                        if not data:
                            break
                        destination.send(data)
                
                t1 = threading.Thread(target=forward, args=(client, local))
                t2 = threading.Thread(target=forward, args=(local, client))
                t1.start()
                t2.start()
                
            except Exception as e:
                print(f"❌ Error: {e}")
                client.close()
                
    except Exception as e:
        print(f"❌ Failed to bind: {e}")

if __name__ == '__main__':
    create_tunnel()
