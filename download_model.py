import os
import gdown

def download_model():
    model_path = os.path.join("models", "best.pt")

    print("Current working directory:", os.getcwd())
    print("Absolute model path:", os.path.abspath(model_path))
    print("Exists:", os.path.exists(model_path))

    file_id = "1KKoe_IXL8avQgvyp2avM0_PRugEDYXjw"
    url = f"https://drive.google.com/uc?id={file_id}"

    if os.path.exists(model_path):
        print(f"{model_path} already exists. Skipping download.")
        return

    os.makedirs("models", exist_ok=True)
    print(f"Downloading {model_path}...")
    output = gdown.download(url, model_path, quiet=False)

    if output and os.path.exists(model_path):
        print("Model downloaded successfully.")
    else:
        raise RuntimeError("Download failed.")

if __name__ == "__main__":
    download_model()
