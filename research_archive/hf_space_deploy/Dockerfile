FROM python:3.11-slim

WORKDIR /app

# Cài torch CPU-only (nhẹ hơn ~10x so với pytorch/pytorch image)
RUN pip install --no-cache-dir \
    torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir \
    torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir \
    gradio==6.10.0 \
    numpy>=1.24.0 \
    Pillow>=10.0.0

COPY . .

EXPOSE 7860

ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

CMD ["python", "app.py"]
