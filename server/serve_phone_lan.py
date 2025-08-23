from server.serve_phone_clean import app
import sys
if __name__ == "__main__":
    port = 8781
    try:
        if len(sys.argv) > 1:
            port = int(sys.argv[1])
    except Exception:
        pass
    app.run(host="0.0.0.0", port=port, debug=False)
