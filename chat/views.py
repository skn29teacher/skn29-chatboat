from django.shortcuts import render

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
        # 최신 가이드를 적용하여 system -> developer 역할로 프롬프트 설정 주입
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {
                    "role": "developer", 
                    "content": "너는 AWS 환경 위에 배포된 똑똑하고 명쾌한 AI 챗봇이야. 항상 정중한 한국어로 간략히 답변해줘."
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        bot_response = response.choices[0].message.content
        return JsonResponse({
            "status": "success",
            "answer": bot_response
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "유효한 JSON 포맷이 아닙니다."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"추론 연동 실패: {str(e)}"}, status=500)
