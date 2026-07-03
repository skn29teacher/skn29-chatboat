# CI/CD 우선형 OpenAI `gpt-5-nano` AWS 챗봇 구축 가이드
*(GitHub Actions + Nginx + Gunicorn + Django + S3 + RDS + OpenAI)*

이 가이드는 AWS 자원이 아무것도 없는 상태에서 시작하여, **"AWS 클라우드 자원 생성 ➡️ EC2 기본 뼈대 구성 ➡️ GitHub Actions CI/CD 자동화 구축 ➡️ 로컬 중심 연동 개발(RDS, S3, OpenAI)"** 순서로 프로젝트를 완수해 나가는 완전 무결한 올인원(All-in-One) 가이드라인입니다.

가이드라인을 따라가다 발생할 수 있는 흔한 에러(깃 설정 누락, 자격 증명 오류, 빌드 크래시, 권한 거부 등)를 사전에 방지하도록 검증 단계를 대폭 강화하였습니다.

---

## 1. [초기 환경 구축] AWS 클라우드 자원 생성 가이드

가상 인프라 구축을 위해 AWS 웹 콘솔에 로그인한 뒤, 아래 순서대로 인프라 자원을 먼저 생성합니다.

### ① IAM 역할 (Role) 생성 (S3 접근 권한 부여)
액세스 키를 코드에 하드코딩하지 않고 EC2 서버 자체가 S3 버킷에 안전하게 접근할 수 있도록 IAM 역할을 부여합니다.

1. AWS 콘솔에서 **IAM** 검색 ➡️ 왼쪽 메뉴 **역할(Roles)** 클릭 ➡️ **역할 만들기** 클릭
2. 신뢰할 수 있는 엔터티 유형: **AWS 서비스** 선택
3. 서비스 또는 사례: **EC2** 선택 ➡️ 하단의 EC2 라디오 버튼 체크 후 **다음** 클릭
4. 권한 정책 추가: 검색창에 **`AmazonS3FullAccess`** 검색 후 체크 ➡️ **다음** 클릭
5. 역할 이름: **`skn29-ec2-s3-role`** 입력 ➡️ **역할 생성** 클릭

---

### ② 보안 그룹 (Security Group) 생성
네트워크 방화벽 역할을 하는 보안 그룹을 웹서버용과 DB용으로 각각 생성합니다.

#### 1. 웹서버 보안 그룹 (`skn29-django-sg`)
1. AWS 콘솔에서 **VPC** 또는 **EC2** 검색 ➡️ 왼쪽 메뉴 **보안 그룹** ➡️ **보안 그룹 생성** 클릭
2. 보안 그룹 이름: **`skn29-django-sg`**
3. 설명: `Django Web Server Security Group`
4. **인바운드 규칙(Inbound Rules) 추가**:
   * **규칙 1**: 유형 `SSH` (22 포트) / 소스 `Anywhere-IPv4` (`0.0.0.0/0`) (GitHub Actions 배포 서버가 SSH로 EC2에 접속할 수 있도록 Anywhere로 열어주어야 합니다. 비밀키인 `.pem` 키가 없으면 외부에서 절대 로그인할 수 없으므로 안전합니다.)
   * **규칙 2**: 유형 `HTTP` (80 포트) / 소스 `Anywhere-IPv4` (`0.0.0.0/0`)
   * **규칙 3**: 유형 `HTTPS` (443 포트) / 소스 `Anywhere-IPv4` (`0.0.0.0/0`)
5. **보안 그룹 생성** 클릭

#### 2. 데이터베이스 보안 그룹 (`skn29-rds-sg`)
1. 동일하게 **보안 그룹 생성** 클릭
2. 보안 그룹 이름: **`skn29-rds-sg`**
3. 설명: `PostgreSQL RDS Security Group`
4. **인바운드 규칙 추가**:
   * 유형: **`PostgreSQL`** (5432 포트 자동 지정)
   * 소스: 사용자 지정 선택 후, 우측 검색 칸을 눌러 위에서 만든 **`skn29-django-sg`** 선택 (EC2 웹서버에서만 DB에 들어올 수 있도록 차단 설정)
5. **보안 그룹 생성** 클릭

---

### ③ EC2 인스턴스 생성 및 탄력적 IP 연결

#### 1. EC2 인스턴스 생성
1. AWS 콘솔에서 **EC2** 검색 ➡️ **인스턴스 시작** 클릭
2. 이름: **`skn29-django-server`**
3. AMI(운영체제): **Ubuntu Server 26.04 LTS** (또는 최신 LTS 버전)
4. 인스턴스 유형: **`t3.micro`** (프리티어 대상)
5. 키 페어: 새 키 페어 생성 클릭 ➡️ 이름 **`skn29-key`**, 형식 **`.pem`** ➡️ 키 페어 생성 및 다운로드 (다운로드한 `.pem` 파일은 절대 잃어버리지 않도록 안전한 폴더에 보관)
6. 네트워크 설정 ➡️ **기존 보안 그룹 선택** 체크 ➡️ **`skn29-django-sg`** 보안 그룹 체크
7. 스토리지 구성: 기본 8GB를 프리티어 최대 사양인 **`20GB gp3`**로 변경
8. **인스턴스 시작** 클릭
9. **IAM 역할(Role) 연결 (필수!)**: 인스턴스 생성 완료 후, 인스턴스 목록에서 `skn29-django-server` 선택 ➡️ 우측 상단의 **작업(Actions)** ➡️ **보안(Security)** ➡️ **IAM 역할 수정(Modify IAM role)** 클릭 ➡️ 위에서 만든 **`skn29-ec2-s3-role`**을 선택하고 **IAM 역할 업데이트(Update IAM role)**를 클릭하여 최종 매핑합니다.

#### 2. 탄력적 IP (Elastic IP) 할당 및 연결 (서버 고정 IP 확보)
*서버를 껐다 켜도 IP 주소가 바뀌지 않도록 고정 IP를 매핑합니다.*
1. EC2 콘솔 왼쪽 메뉴 ➡️ **탄력적 IP** ➡️ **탄력적 IP 주소 할당** 클릭 ➡️ 하단 **할당** 클릭
2. 생성된 탄력적 IP 선택 ➡️ 우측 상단 **작업** ➡️ **탄력적 IP 주소 연결** 클릭
3. 리소스 유형: 인스턴스 ➡️ 인스턴스 검색 칸에서 `skn29-django-server` 선택 ➡️ 하단 **연결** 클릭

---

### ④ RDS (PostgreSQL) 데이터베이스 생성
1. AWS 콘솔에서 **RDS** 검색 ➡️ 왼쪽 메뉴 **데이터베이스** ➡️ **데이터베이스 생성** 클릭
2. 생성 방식: **표준 생성** ➡️ 엔진 옵션: **PostgreSQL** 선택
3. 템플릿: **프리 티어** 선택
4. 설정:
   * DB 인스턴스 식별자: **`skn29-django-db`**
   * 마스터 사용자 이름: **`postgres`**
   * 마스터 암호: 본인이 사용할 **보안성 높은 암호 입력 및 별도 기록**
5. 인스턴스 구성: **`db.t3.micro`** 또는 **`db.t4g.micro`**
6. 스토리지: **`gp3`**, 할당된 스토리지 **`20GB`** (스토리지 자동 조정 활성화는 비용 절감을 위해 체크 해제 권장)
7. 연결:
   * **퍼블릭 액세스**: **아니요** (보안 표준: 외부에서는 접속 불가하게 막고 VPC 내부의 EC2만 우회 연결하도록 설정)
   * VPC 보안 그룹: **기존 항목 선택** ➡️ 기본 지정된 default 그룹 해제 후, 위에서 만든 **`skn29-rds-sg`** 선택
8. **추가 구성** (맨 아래 아코디언 메뉴 클릭하여 펼치기):
   * **초기 데이터베이스 이름**: **`chatbotdb`** 입력 (이 값을 입력해 두어야 장고가 바로 연결하여 테이블을 생성할 수 있는 최초의 공간이 마련됩니다)
9. 맨 아래 **데이터베이스 생성** 클릭 (구축 완료 및 상태가 '사용 가능'으로 변할 때까지 약 5~10분 소요됩니다. **이후 단계를 진행하는 동안 백그라운드에서 완전히 생성 완료될 때까지 기다리셔야 합니다**)

---

### ⑤ S3 버킷 생성 및 버킷 정책 설정
웹 화면을 그리는 정적 리소스(CSS/JS)를 브라우저에 뿌려주기 위해 S3 버킷을 열고 퍼블릭 읽기 권한을 부여합니다.

1. AWS 콘솔에서 **S3** 검색 ➡️ **버킷 만들기** 클릭
2. 버킷 이름: **`skn29-django-static-<본인 고유 식별값>`** 입력 (S3 이름은 전 세계 유일해야 하므로 본인 영문 이름 이니셜 등을 뒤에 붙입니다)
3. 객체 소유권: **ACL 비활성화됨(권장)** 선택
4. **이 버킷의 퍼블릭 액세스 차단 설정**:
   * **`모든 퍼블릭 액세스 차단` 체크 해제**
   * 하단에 나타나는 '현재 설정으로 인해... 알고 있습니다' 체크박스 체크 (사용자의 브라우저가 정적 디자인 파일들을 무리 없이 다운로드해 갈 수 있도록 퍼블릭 읽기 권한의 통로를 열어두는 과정입니다)
5. 맨 아래 **버킷 만들기** 클릭
6. 생성된 버킷 이름을 클릭해 들어간 뒤, 상단 **권한 (Permissions)** 탭 클릭
7. 스크롤을 내려 **버킷 정책 (Bucket policy)** 우측의 **편집(Edit)** 클릭 ➡️ 아래 JSON 복사/붙여넣기:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Sid": "PublicReadGetObject",
               "Effect": "Allow",
               "Principal": "*",
               "Action": "s3:GetObject",
               "Resource": "arn:aws:s3:::<자신의_버킷_이름>/*"
           }
       ]
   }
   ```
   * *주의: `<자신의_버킷_이름>` 부분을 실제 본인이 생성한 버킷 명칭으로 수정해야 합니다.*
8. **변경 사항 저장** 클릭

---

## 2. 개발 프로세스 설계 및 데이터 흐름

모든 클라우드 자원의 셋팅이 끝났습니다. 이제 이 자원들을 유기적으로 결합하여 코딩하기 위해 구축할 개발 자동화 아키텍처와 요청 처리 순서는 다음과 같습니다.

### 🔄 개발 작업 흐름 (Workflow)
```
[로컬 PC에서 수정] ──(git push)──> [GitHub Repository] ──(자동 배포)──> [GitHub Actions] 
                                                                               │ (SSH 원격 제어)
                                                                               ▼
                                                                        [AWS EC2 서버]
                                                                  (배포 스크립트 실행 및 반영)
```

### 🖥️ 시스템 아키텍처 및 데이터 흐름
```
[사용자 브라우저]
       ↓ (HTTP 요청)
    [Nginx] (리버스 프록시 / 정적 파일 서빙)
       ↓ (유닉스 소켓: gunicorn.sock)
   [Gunicorn] (WSGI 미들웨어 서버)
       ↓ (장고 앱 구동)
   [Django] 
      ├── [RDS (PostgreSQL)]  ← (데이터베이스 연동)
      ├── [S3 (Bucket)]       ← (정적/미디어 파일 위임)
      └── [OpenAI API]        ← (gpt-5-nano 실시간 추론)
```

---

## 3. [서버 최초 1회] EC2 기본 뼈대 초기 설정

자동 배포 스크립트가 EC2에서 정상적으로 명령을 수행하려면, 최초 1회 서버 디렉토리 구조와 Gunicorn/Nginx의 기본 뼈대가 만들어져 있어야 합니다.

### ① 서버 패키지 설치 및 디렉토리 구성
탄력적 IP(EIP) 주소를 복사한 뒤, 다운로드해 둔 `.pem` 키를 사용해 터미널 또는 MobaXterm으로 EC2 서버에 SSH 접속을 진행합니다.
```bash
# 서버 패키지 업데이트 및 빌드 도구 설치
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-dev git build-essential libpq-dev nginx

# 프로젝트 디렉토리 생성 및 가상환경 활성화
mkdir ~/myproject && cd ~/myproject
python3 -m venv venv
source venv/bin/activate

# 필수 패키지 임시 설치 및 최초 프로젝트 생성
pip install django gunicorn
django-admin startproject config .
```

프로젝트 생성 후 `config/settings.py` 파일을 열어 다음 설정을 진행합니다.
```bash
nano config/settings.py
```
* **ALLOWED_HOSTS 수정**:
  ```python
  ALLOWED_HOSTS = ['<EC2 탄력적 IP>', 'localhost', '127.0.0.1']
  ```
* **STATIC_ROOT 설정 추가 (중요!)**:
  *초기 배포 단계에서 `collectstatic` 명령어가 오동작하여 빌드가 깨지는 것을 방지하기 위해 파일 맨 아래에 다음 설정을 명시적으로 추가합니다.*
  ```python
  import os
  STATIC_ROOT = os.path.join(BASE_DIR, 'static/')
  ```

이후 초기 데이터베이스 동기화를 수행합니다.
```bash
python manage.py migrate
```

### ② Gunicorn 서비스 생성 (`/etc/systemd/system/gunicorn.service`)
```bash
sudo nano /etc/systemd/system/gunicorn.service
```
아래 내용을 입력하고 저장합니다.
```ini
[Unit]
Description=gunicorn daemon for Django Chatbot
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/myproject
ExecStart=/home/ubuntu/myproject/venv/bin/gunicorn \
          --workers 3 \
          --bind unix:/home/ubuntu/myproject/gunicorn.sock \
          --umask 007 \
          --timeout 120 \
          config.wsgi:application

[Install]
WantedBy=multi-user.target
```
> [!NOTE]
> 1. AI 추론(Inference)은 일반 웹 요청에 비해 응답 지연(Latency)이 발생하므로, Gunicorn 구동 옵션에 `--timeout 120`을 주어 웹서버 연결 끊김(502 Bad Gateway) 에러를 사전에 방지합니다.
> 2. Nginx가 Gunicorn 소켓 파일에 권한 문제(Permission Denied) 없이 접근할 수 있도록 `--umask 007`을 추가하였습니다.

### ③ Nginx 리버스 프록시 설정 (`/etc/nginx/sites-available/myproject`)
```bash
sudo nano /etc/nginx/sites-available/myproject
```
아래 설정을 입력하여 포트 80(HTTP) 요청을 Gunicorn 소켓으로 흐르게 프록시 처리합니다.
```nginx
server {
    listen 80;
    server_name <EC2 탄력적 IP>;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /home/ubuntu/myproject/static/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/myproject/gunicorn.sock;
        proxy_read_timeout 120s;
        proxy_connect_timeout 120s;
    }
}
```
설정 반영 및 서비스 활성화:
```bash
sudo ln -s /etc/nginx/sites-available/myproject /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo chmod 755 /home/ubuntu
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl restart nginx
```

---

## 4. [CI/CD 구축] GitHub Actions 배포 자동화 구현

여기서부터 본격적인 **CI/CD 환경 설정**에 돌입합니다. 이 단계를 마치면 더 이상 EC2 서버에 SSH로 접속해 코드를 만질 필요가 없어집니다.

### ① EC2 프로젝트 Git 초기화 및 최초 Push
서버에 생성된 기본 Django 뼈대 소스코드를 GitHub 저장소에 밀어 넣습니다.

> [!WARNING]
> GitHub에서 저장소(Repository)를 최초 생성할 때, **README.md, .gitignore, License 등 어떠한 초기화 옵션도 체크하지 않은 완전히 빈(Empty) 저장소 상태로 생성**해야 첫 `git push`가 Reject(거절)되지 않고 성공합니다.

```bash
# EC2 터미널에서 실행
cd ~/myproject
git init
git remote add origin https://github.com/<본인_GitHub_ID>/django-chatbot-preview.git

# 깃 사용자 정보 글로벌 등록 (이름/이메일 누락 시 최초 git commit 시 에러가 납니다!)
git config --global user.email "your-email@example.com"
git config --global user.name "Your Name"

# requirements.txt 파일 생성
pip freeze > requirements.txt

# 민감 정보 보호를 위해 .gitignore 작성
echo ".env" >> .gitignore
echo "venv/" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "db.sqlite3" >> .gitignore

# 깃 자격 증명 캐싱 활성화 (최초 1회 실행 필수!)
# 이 설정을 켜야 자동 배포 도중 GitHub Actions가 Git Pull을 받을 때 자격 증명을 계속 물어보는 멈춤 현상이 발생하지 않습니다.
git config --global credential.helper store

# 커밋, 브랜치명 변경 및 최초 푸시
git add .
git commit -m "Initial skeleton setup"
git branch -M main
git push -u origin main
```
> [!IMPORTANT]
> `git push` 실행 시 GitHub 아이디와 패키지 연동을 위해 발급한 **Classic Token(PAT)** 값을 입력하여 인증을 성공시켜야 하며, 이를 통해 자격 증명이 EC2 서버에 보관되어 이후 GitHub Actions가 비밀번호 입력 요구 없이 코드를 받아갈(`git pull`) 수 있게 됩니다.

### ② GitHub Secrets 등록
GitHub 저장소 페이지 -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**으로 접속하여 아래 3개의 변수를 등록합니다.

* `EC2_HOST`: EC2 퍼블릭 IP 주소
* `EC2_USER`: `ubuntu`
* `EC2_SSH_KEY`: EC2 접속 시 사용하는 `.pem` 키 내용 전체 복사 (메모장으로 열어 첫 줄부터 끝 줄까지 그대로 복사)

### ③ 로컬 PC로 프로젝트 복제(Clone)
이제 작업공간을 로컬 PC의 IDE(VS Code 등)로 옮깁니다. 로컬 터미널을 열고 코드를 내려받습니다.
```bash
# 로컬 PC 터미널에서 실행
git clone https://github.com/<본인_GitHub_ID>/django-chatbot-preview.git
cd django-chatbot-preview

# 로컬 가상환경 및 패키지 설치
# Windows
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### ④ 배포 워크플로 파일 생성
로컬 PC 프로젝트 루트에 `.github/workflows/deploy.yml` 파일을 생성합니다.
```yaml
name: Deploy Chatbot to EC2

on:
  push:
    branches: [ main ] # main 브랜치로 push 발생 시 배포 구동

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: SSH Connection and Auto Deploy
        uses: appleboy/ssh-action@v1.2.2
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USER }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd ~/myproject
            source venv/bin/activate
            git pull origin main
            pip install -r requirements.txt
            python manage.py migrate --noinput
            python manage.py collectstatic --noinput
            sudo systemctl restart gunicorn
```

작성이 끝났으면 첫 번째 자동 배포 테스트를 수행합니다.
```bash
git add .
git commit -m "Add GitHub Actions workflow"
git push origin main
```
GitHub 저장소의 **Actions** 탭에서 초록색 체크마크가 뜨고 배포가 끝나는 것을 확인합니다. **이후 모든 과정은 로컬 PC에서만 진행합니다.**

---

## 5. [로컬 작업 1] RDS(PostgreSQL) 연동

이제 로컬 PC에서 장고 설정을 다루며 클라우드 데이터베이스를 연동합니다.

> [!WARNING]
> **중요 (진행 순서 준수)**: 데이터베이스 생성(Status: Available)이 완료되었는지 확인한 후에 이 단계를 진행해야 연결 에러가 나지 않습니다.

### ① 로컬 패키지 추가
로컬 터미널에서 PostgreSQL 드라이버 및 환경변수 로더를 설치합니다.
```bash
pip install psycopg2-binary python-dotenv
pip freeze > requirements.txt
```

### ② 로컬 및 EC2 서버 각각 `.env` 파일 작성 (★ 필수)
프로젝트 루트 디렉토리에 로컬 전용 `.env` 파일을 생성하고 AWS RDS 데이터베이스 접속 정보를 기재합니다.
```env
DB_NAME=chatbotdb
DB_USER=postgres
DB_PASSWORD=your_rds_master_password
DB_HOST=your-rds-endpoint.xxxx.ap-northeast-2.rds.amazonaws.com
DB_PORT=5432
```
> [!IMPORTANT]
> **가장 흔히 저지르는 오류 방지**: `.env` 파일은 보안상 Git에 커밋되지 않습니다. 따라서 로컬 코드를 깃허브에 push하기 전에, **먼저 EC2 서버 터미널에 SSH로 직접 접속하여 `~/myproject/.env` 파일을 위 내용과 똑같이 수동으로 작성해 주어야 합니다.**
> 이 작업을 건너낀 채 코드를 push하면, 깃허브 액션 배포 스크립트가 EC2 환경변수를 찾지 못해 `python manage.py migrate` 명령 실행 도중 비정상 종료되고 배포에 실패하게 됩니다.

### ③ `config/settings.py` 수정
```python
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}
```

### ④ Git Push 및 자동 배포
```bash
git add .
git commit -m "Configure RDS PostgreSQL connection"
git push origin main
```
배포가 완료되면 Actions가 알아서 EC2 서버 상에서 `python manage.py migrate`를 돌려 RDS 테이블 스키마를 초기화합니다.

---

## 6. [로컬 작업 2] S3 정적/미디어 파일 연동

정적 자산과 업로드 이미지를 AWS S3 스토리지로 이관합니다.

### ① 패키지 추가 설치
```bash
pip install django-storages boto3
pip freeze > requirements.txt
```

### ② `config/settings.py` 스토리지 설정 변경
```python
# settings.py 상단 INSTALLED_APPS에 'storages' 앱을 추가합니다.
INSTALLED_APPS = [
    # ... 기본 앱 ...
    'storages',
]

# S3 버킷 설정 (EC2에 S3 FullAccess IAM 역할이 매핑되어 있으므로 Access Key는 기재 불필요)
AWS_STORAGE_BUCKET_NAME = 'your-s3-bucket-name' # 자신이 실제 생성한 버킷명 기재
AWS_S3_REGION_NAME = 'ap-northeast-2'
AWS_QUERYSTRING_AUTH = False 

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
    },
}
```
> [!TIP]
> **로컬 개발환경 팁**: 로컬 PC에서 `python manage.py runserver` 실행 시 로컬 AWS 자격 증명 누락으로 인해 `NoCredentialsError`가 발생한다면, 로컬 PC의 `.env` 파일 하단에 `AWS_ACCESS_KEY_ID=dummy`, `AWS_SECRET_ACCESS_KEY=dummy`를 추가하여 우회하면 됩니다.

### ③ Git Push 및 자동 배포
```bash
git add .
git commit -m "Configure AWS S3 storage backend"
git push origin main
```
자동 배포가 돌면서 `collectstatic` 명령어를 통해 장고의 기본 관리자 페이지 디자인 자산(`admin/`)들이 S3 버킷으로 업로드되는 것을 S3 콘솔에서 확인할 수 있습니다.

---

## 7. [로컬 작업 3] OpenAI `gpt-5-nano` AI 추론 연동

이제 마지막 단계로 AI 추론을 받아 답변하는 핵심 챗봇 백엔드를 연동합니다.

### ① 패키지 설치 및 앱 생성
```bash
pip install openai
pip freeze > requirements.txt

# 로컬에서 chat 앱 생성
python manage.py startapp chat
```

### ② `config/settings.py` 등록 및 환경 변수 연동
`INSTALLED_APPS` 목록에 `'chat',` 앱을 추가하고, 파일 하단에 OpenAI API Key 설정을 작성해 줍니다.
```python
INSTALLED_APPS = [
    # ... 기본 앱 ...
    'storages',
    'chat',
]

# OpenAI API Key 로드
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```

### ③ `.env` 파일에 OpenAI API Key 추가 (로컬 및 EC2 각각 추가 필요)
* 로컬의 `.env` 및 EC2 서버의 `.env` 파일 하단에 API 키를 기록합니다.
```env
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
```
> [!IMPORTANT]
> 이 키 역시 코드를 push하기 전에 **로컬과 EC2 서버 양쪽의 `.env` 파일에 미리 등록**해 주어야 추론 요청 및 배포 도중에 에러가 발생하는 것을 방지할 수 있습니다.

### ④ AI 추론 뷰 구현 (`chat/views.py`)
OpenAI 최신 API 가이드라인(SDK v1.0.0+ 기준) 및 최신 경량 고효율 모델 `gpt-5-nano`에 맞춰 소스코드를 작성합니다. 시스템 페르소나 지시사항에는 `system` 대신 최신의 **`developer`** 역할을 적용합니다.

> [!TIP]
> **성능 및 아키텍처 팁 (Lazy Initialization)**:
> `client = OpenAI(...)` 객체를 모듈 레벨(최상단)에서 선언하면 장고가 켜질 때 API Key 검사를 수행하여 키가 없는 경우 서버 시작 자체가 불가능해집니다(502 Bad Gateway). 이를 예방하기 위해 아래와 같이 `chat_view` 함수 내부에서 요청이 올 때 인스턴스화되도록 안전하게 구성하였습니다.

```python
import os
import json
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from openai import OpenAI

@csrf_exempt
@require_http_methods(["POST"])
def chat_view(request):
    """
    사용자의 질문을 수신하여 OpenAI gpt-5-nano 모델로 추론을 위임 및 응답하는 API
    """
    try:
        body = json.loads(request.body)
        user_message = body.get("message", "").strip()
        
        if not user_message:
            return JsonResponse({"error": "메시지 필드가 비어있습니다."}, status=400)
            
        # Django 설정에서 API 키를 가져와 요청 발생 시 안전하게 생성 (Lazy)
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # gpt-5-nano 모델 호출 및 추론
        # 2026년 최신 표준: 레거시 chat.completions.create 대신 Responses API(responses.create) 적용
        response = client.responses.create(
            model="gpt-5-nano",
            input=user_message,
            instructions="너는 AWS 환경 위에 배포된 똑똑하고 명쾌한 AI 챗봇이야. 항상 정중한 한국어로 간략히 답변해줘."
        )
        
        bot_response = response.output_text
        return JsonResponse({
            "status": "success",
            "answer": bot_response
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "유효한 JSON 포맷이 아닙니다."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"추론 연동 실패: {str(e)}"}, status=500)
```

### ⑤ 웹 UI 템플릿 작성 (`chat/templates/chat/index.html`)
사용자가 웹브라우저에서 직접 채팅을 주고받을 수 있도록 간단한 부트스트랩 디자인이 포함된 HTML 템플릿을 생성합니다.

* **로컬 파일 경로**: `chat/templates/chat/index.html` (가상환경 루트 폴더 하위에 폴더가 없으면 새로 만듭니다.)

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS AI Chatbot - gpt-5-nano</title>
    <!-- Bootstrap 5.3 CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #f4f6f9;
        }
        .chat-container {
            max-width: 600px;
            margin: 50px auto;
        }
        .chat-card {
            border: none;
            border-radius: 16px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
        }
        .chat-header {
            border-top-left-radius: 16px !important;
            border-top-right-radius: 16px !important;
            background: linear-gradient(135deg, #0d6efd, #0a58ca);
        }
        .chat-body {
            height: 480px;
            overflow-y: auto;
            background-color: #ffffff;
            padding: 24px;
        }
        .message {
            margin-bottom: 20px;
            max-width: 80%;
            padding: 12px 18px;
            border-radius: 16px;
            font-size: 0.95rem;
            line-height: 1.5;
            word-break: break-all;
        }
        .message.user {
            background-color: #0d6efd;
            color: #ffffff;
            margin-left: auto;
            border-bottom-right-radius: 2px;
        }
        .message.bot {
            background-color: #f1f3f5;
            color: #212529;
            margin-right: auto;
            border-bottom-left-radius: 2px;
        }
        .loading-spinner {
            display: none;
        }
    </style>
</head>
<body>

<div class="container">
    <div class="chat-container">
        <div class="card chat-card">
            <!-- 챗봇 상단 헤더 -->
            <div class="card-header chat-header text-white text-center py-3">
                <h5 class="mb-0 fw-bold">AWS AI Chatbot Preview</h5>
                <small class="opacity-75">OpenAI gpt-5-nano</small>
            </div>
            
            <!-- 채팅 본문 로그 영역 -->
            <div class="card-body chat-body" id="chatBody">
                <div class="message bot">
                    안녕하세요! 무엇을 도와드릴까요? (OpenAI <strong>gpt-5-nano</strong> 모델과 실시간으로 통신합니다.)
                </div>
            </div>
            
            <!-- 메시지 입력 영역 -->
            <div class="card-footer p-3 bg-white" style="border-bottom-left-radius: 16px; border-bottom-right-radius: 16px;">
                <form id="chatForm" onsubmit="sendMessage(event)">
                    <div class="input-group">
                        <input type="text" id="messageInput" class="form-control py-2" placeholder="메시지를 입력하세요..." required autocomplete="off">
                        <button class="btn btn-primary px-4" type="submit" id="sendBtn">
                            <span class="send-text">전송</span>
                            <span class="spinner-border spinner-border-sm loading-spinner" role="status" aria-hidden="true"></span>
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>

<script>
    const chatBody = document.getElementById('chatBody');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const sendText = sendBtn.querySelector('.send-text');
    const spinner = sendBtn.querySelector('.loading-spinner');

    function appendMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', sender);
        // HTML 이스케이프 및 줄바꿈 처리
        msgDiv.innerHTML = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>");
        chatBody.appendChild(msgDiv);
        chatBody.scrollTop = chatBody.scrollHeight; // 스크롤 하단 고정
    }

    async function sendMessage(event) {
        event.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        // 화면에 사용자 메시지 출력
        appendMessage(message, 'user');
        messageInput.value = '';

        // 전송 버튼 대기 상태 활성화
        sendBtn.disabled = true;
        sendText.style.display = 'none';
        spinner.style.display = 'inline-block';

        try {
            // 장고 백엔드 API로 비동기 요청 전송
            const response = await fetch('/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                appendMessage(data.answer, 'bot');
            } else {
                appendMessage("에러 발생: " + (data.error || "알 수 없는 오류"), 'bot');
            }
        } catch (error) {
            appendMessage("네트워크 연결 실패: " + error.message, 'bot');
        } finally {
            // 버튼 상태 원복
            sendBtn.disabled = false;
            sendText.style.display = 'inline-block';
            spinner.style.display = 'none';
        }
    }
</script>
</body>
</html>
```

### ⑥ `chat/views.py` 뷰 추가 수정
사용자에게 HTML 화면을 제공하는 `index_view`를 뷰 파일에 추가합니다.

* **로컬 파일 경로**: `chat/views.py`

```python
import os
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from openai import OpenAI

def index_view(request):
    """챗봇 메인 HTML UI 화면을 렌더링합니다."""
    return render(request, 'chat/index.html')

@csrf_exempt
@require_http_methods(["POST"])
def chat_view(request):
    """
    사용자의 질문을 수신하여 OpenAI gpt-5-nano 모델로 추론을 위임 및 응답하는 API
    """
    try:
        body = json.loads(request.body)
        user_message = body.get("message", "").strip()
        
        if not user_message:
            return JsonResponse({"error": "메시지 필드가 비어있습니다."}, status=400)
            
        # settings.py에서 키를 가져와 요청 발생 시 안전하게 1회성 생성 (Lazy)
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # 2026년 최신 표준: 레거시 chat.completions.create 대신 Responses API(responses.create) 적용
        response = client.responses.create(
            model="gpt-5-nano",
            input=user_message,
            instructions="너는 AWS 환경 위에 배포된 똑똑하고 명쾌한 AI 챗봇이야. 항상 정중한 한국어로 간략히 답변해줘."
        )
        
        bot_response = response.output_text
        return JsonResponse({
            "status": "success",
            "answer": bot_response
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "유효한 JSON 포맷이 아닙니다."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"추론 연동 실패: {str(e)}"}, status=500)
```

### ⑦ 라우팅 설정 (`chat/urls.py` & `config/urls.py`)
메인 화면(`/`)과 대화 API 엔드포인트(`/api/chat/`)가 정상 동작하도록 URL을 매핑합니다.

* **`chat/urls.py`**
```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='chat_index'),       # 메인 채팅 웹 UI 화면
    path('api/chat/', views.chat_view, name='chat_view'), # AI 추론 API 엔드포인트
]
```

* **`config/urls.py`**
```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('chat.urls')),
]
```

### ⑧ Git Push 및 최종 자동 배포
추가한 템플릿과 뷰, URL 매핑 설정 파일을 로컬 Git을 사용해 커밋하고 push합니다.
```bash
git add .
git commit -m "Implement Bootstrap Web UI and routes"
git push origin main
```
자동 배포가 성공(Actions 초록 체크)하면, EC2 서버가 변경사항을 풀하고 Gunicorn을 재기동합니다.

---

## 8. 최종 웹 UI 및 AI 추론 검증

모든 배포가 끝났습니다. 이제 실제 웹 브라우저와 터미널에서 AI 추론이 조화롭게 결합되어 동작하는지 검증합니다.

### ① 웹 브라우저 접속 검증 (★ 가장 확실한 시각적 테스트)
1. 웹 브라우저(Chrome 등)를 켭니다.
2. 주소창에 내 **EC2 탄력적 IP**를 입력하고 접속합니다:
   `http://<EC2_PUBLIC_IP>/`
3. 파란색 헤더의 **AWS AI Chatbot Preview** 디자인 화면이 로딩되면 성공입니다.
4. 하단 입력창에 질문을 작성한 뒤 **전송** 버튼을 누릅니다.
5. 로딩 표시(Spinner)가 돌며 수초 이내에 OpenAI `gpt-5-nano` 모델의 한국어 답변이 대화창에 정상적으로 쌓이면 실시간 AI 웹앱 추론 사이클 구축이 완료된 것입니다.

### ② API 단독 추론 검증 (터미널 cURL 테스트)
로컬 PC 터미널에서 API만 단독 테스트하고 싶을 때 실행합니다. (CMD/PowerShell의 경우 따옴표 이스케이프에 주의하세요.)

* **MobaXterm Local Terminal / Git Bash (추천)**:
  ```bash
  curl -X POST http://<EC2_PUBLIC_IP>/api/chat/ \
    -H "Content-Type: application/json" \
    -d '{"message": "안녕! 사용 중인 인공지능 모델 이름이 뭐야?"}'
  ```

* **Windows CMD**:
  ```cmd
  curl -X POST http://<EC2_PUBLIC_IP>/api/chat/ -H "Content-Type: application/json" -d "{\"message\": \"안녕! 사용 중인 인공지능 모델 이름이 뭐야?\"}"
  ```

* **Windows PowerShell**:
  ```powershell
  curl.exe -X POST http://<EC2_PUBLIC_IP>/api/chat/ -H "Content-Type: application/json" -d "{\"message\": \"안녕! 사용 중인 인공지능 모델 이름이 뭐야?\"}"
  ```

### 예상 응답 JSON
```json
{
  "status": "success",
  "answer": "안녕하세요! 저는 AWS 서버 위에서 작동 중인 AI 비서입니다. 저는 현재 OpenAI의 최신 고효율 모델인 `gpt-5-nano` 모델을 사용하여 답변을 드리고 있습니다."
}
```