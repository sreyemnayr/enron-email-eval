import requests


def check_health():
    try:
        response = requests.get("http://inference-server:80/health")
        if response.status_code != 200:
            return False
        return True
    except Exception as e:
        return False


def check_ollama():
    try:
        response = requests.get("http://host.docker.internal:11434")
        if response.status_code != 200:
            return False
        return True
    except Exception as e:
        return False
