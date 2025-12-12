import uvicorn

if __name__ == "__main__":
    # Run the API server
    # Listen on localhost:8000 for FRP
    uvicorn.run("vivia_v4.api.main:app", host="127.0.0.1", port=8000, reload=True,
                ssl_keyfile="skinkebravia.top_private.key", ssl_certfile="skinkebravia.top_full.crt")
