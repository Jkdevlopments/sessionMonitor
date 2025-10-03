from pyngrok import ngrok

# Start ngrok tunnel
public_url = ngrok.connect(3000)
print("Public URL:", public_url)
