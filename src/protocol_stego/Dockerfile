FROM python:3.11-slim

WORKDIR /work

COPY protocol_stego/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r /tmp/requirements.txt

COPY crypto /work/crypto
COPY protocol_stego /work/protocol_stego

ENV PYTHONPATH=/work:/work/protocol_stego \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /work/protocol_stego

CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
