FROM zepai/graphiti:latest

USER root

# scikit-learn 설치 (uv 활용)
RUN uv pip install --no-cache-dir scikit-learn

# 로그 저장을 위한 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/logs && chown -p app:app /app/logs

USER app