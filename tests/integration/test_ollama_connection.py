
import httpx
import pytest
from src.core.config import settings

@pytest.mark.asyncio
async def test_ollama_server_connection():
    """Ollama 서버(Docker)와 통신이 가능한지 확인"""
    url = f"{settings.OLLAMA_URL}/api/tags"
    print(f"\n[Test] Connecting to Ollama at: {url}")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            
        print(f"[Test] Status Code: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        models = [model['name'] for model in data.get('models', [])]
        print(f"[Test] Available Models in Container: {models}")
        
        # 모델이 하나도 없으면 경고 출력
        if not models:
            print("[Warning] No models found in Ollama container. Run 'docker exec -it <container_id> ollama pull gemma2:2b'")
            
    except Exception as e:
        pytest.fail(f"Ollama server is unreachable at {url}. Error: {e}")

@pytest.mark.asyncio
async def test_ollama_model_ready():
    """설정된 특정 모델(gemma2:2b)이 로드되어 있는지 확인"""
    target_model = settings.OLLAMA_MODEL
    url = f"{settings.OLLAMA_URL}/api/tags"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        
    models = [model['name'] for model in data.get('models', [])]
    # 모델명은 'gemma2:2b' 또는 'gemma2:2b-latest' 등으로 표기될 수 있음
    assert any(target_model in m for m in models), f"Model '{target_model}' is not pulled in the container."
    print(f"[Test] Model '{target_model}' is READY.")
