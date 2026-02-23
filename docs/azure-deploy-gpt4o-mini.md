# Azure에서 gpt-4o-mini 배포 추가하기

**중요:** Azure에서는 **기존 배포의 모델을 바꿀 수 없습니다.**  
gpt-4.1 배포를 gpt-4o-mini로 "수정"하는 것은 불가능하고, **gpt-4o-mini용 새 배포를 하나 더 만든 뒤** 코드에서 그 배포 이름을 쓰면 됩니다.

---

## 방법 1: Microsoft Foundry (클래식) 포털에서 배포 추가

### 1단계: 포털 접속

1. 브라우저에서 **https://ai.azure.com** 접속 후 로그인
2. 오른쪽 상단 **"New Foundry"** 토글이 있으면 **끄기** (클래식 화면 사용)
3. **"Keep building with Foundry"** 영역에서 **"View all resources"** 클릭

### 2단계: 리소스 선택

1. 목록에서 사용 중인 **Azure OpenAI 리소스** 선택  
   (예: `admin0122-test1-resource`)
2. 업그레이드 안내가 뜨면 **Cancel** 해서 기존 리소스 그대로 사용

### 3단계: 배포(Deployments) 메뉴로 이동

1. 왼쪽 메뉴에서 **"Shared resources"** 섹션 찾기
2. 그 안에 있는 **"Deployments"** 클릭  
   (리소스를 업그레이드했다면 **"My assets"** → **"Models + endpoints"**일 수 있음)

### 4단계: 새 모델 배포 만들기

1. **"+ Deploy model"** (또는 "모델 배포") 버튼 클릭
2. **"Deploy base model"** 선택
3. 모델 목록에서 **gpt-4o-mini** 선택 후 **Confirm** 클릭  
   (목록에 없으면 리전/할당량 문서 확인: [Model summary and region availability](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure?view=foundry-classic#model-summary-table-and-region-availability))
4. 다음 화면에서:
   - **Deployment name:** `gpt-4o-mini` 입력 (원하면 `gpt-4o-mini-01` 등 다른 이름도 가능)
   - **Deployment type:** `Standard` 또는 `Global-Standard` 선택
   - 필요하면 **Tokens per Minute** 등 조정
5. **Deploy** 클릭 후, 상태가 **Succeeded**가 될 때까지 대기

### 5단계: .env에 배포 이름 넣기

배포 이름을 `gpt-4o-mini`로 만들었다면 `.env`에 다음처럼 설정:

```env
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

다른 이름(예: `gpt-4o-mini-01`)으로 만들었다면 그 이름을 그대로 넣으면 됩니다.

---

## 방법 2: Azure Portal에서 리소스 → OpenAI 진입

1. **https://portal.azure.com** 접속
2. 검색창에 **"Azure OpenAI"** 입력 후 서비스 선택
3. 사용 중인 **리소스** 클릭 (예: `admin0122-test1-resource`)
4. 왼쪽 메뉴에서 **"Azure OpenAI Studio에서 열기"** (또는 **"Open in Azure OpenAI Studio"**) 클릭
5. 열린 Studio에서 위 **방법 1의 3단계(Deployments)** 부터 동일하게 진행

---

## 요약

| 하려는 것 | 가능 여부 |
|-----------|-----------|
| 기존 gpt-4.1 배포를 gpt-4o-mini로 **변경** | ❌ 불가 |
| gpt-4o-mini **새 배포 추가** | ✅ 가능 |
| gpt-4.1 배포 삭제 후 같은 이름으로 gpt-4o-mini 배포 생성 | ✅ 가능 (이름 재사용 시에만) |

**권장:** gpt-4.1은 그대로 두고, **gpt-4o-mini** 배포를 새로 만든 뒤 `.env`의 `AZURE_OPENAI_DEPLOYMENT`만 `gpt-4o-mini`로 바꿔서 사용.
