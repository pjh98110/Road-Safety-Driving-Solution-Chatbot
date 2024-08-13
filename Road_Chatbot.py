import streamlit as st
import openai
import google.generativeai as genai
from streamlit_chat import message
import os
import requests
from streamlit_extras.colored_header import colored_header
import pandas as pd

from datetime import datetime, timedelta

# 페이지 구성 설정
st.set_page_config(layout="wide")

openai.api_key = st.secrets["secrets"]["OPENAI_API_KEY"]

if "page" not in st.session_state:
    st.session_state.page = "Home"

if "gpt_api_key" not in st.session_state:
    st.session_state.gpt_api_key = openai.api_key # gpt API Key

if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = st.secrets["secrets"]["GEMINI_API_KEY"]

if 'selected_district' not in st.session_state:
    st.session_state.selected_district = "서울특별시"

# 세션 변수 체크
def check_session_vars():
    required_vars = ['selected_road']
    for var in required_vars:
        if var not in st.session_state:
            st.warning("필요한 정보가 없습니다. 사이드바에서 정보를 입력해 주세요.")
            st.stop()

# 사이드바에서 챗봇 선택
selected_chatbot = st.sidebar.selectbox(
    "(1) 원하는 챗봇을 선택하세요.",
    options=["GPT를 통한 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션 제공 챗봇", "Gemini를 통한 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션 제공 챗봇", "GPT를 통해 어린이보호구역 사고예방 및 안전운전 솔루션 제공 챗봇", 
             "Gemini를 통해 어린이보호구역 사고예방 및 안전운전 솔루션 제공 챗봇", "GPT를 통한 교통사고 위험도에 따른 사고예방 솔루션 제공 챗봇", "Gemini를 통한 교통사고 위험도에 따른 사고예방 솔루션 제공 챗봇"],
    help="선택한 챗봇에 따라 맞춤형 결과물을 제공합니다."
)

# 사이드바에서 도로상태 선택
selected_road = st.sidebar.selectbox(
    "(2) 예상되는 도로상태를 선택하세요:",
    ('포트홀', '블랙아이스', '수막현상', '도로노후')
)
st.session_state.selected_road = selected_road

# 사이드바에서 탑승차종 선택
selected_car = st.sidebar.selectbox(
    "(3) 탑승차종을 선택하세요:",
    ('승용차', '승합차', '화물차', '이륜차', '자전거', '전동킥보드')
)
st.session_state.selected_car = selected_car

# 사이드바에서 지역 선택
selected_district = st.sidebar.selectbox(
    "(4) 당신의 지역을 선택하세요:",
    ('서울특별시', '경기도', '부산광역시', '인천광역시', '충청북도', '충청남도', 
    '세종특별자치시', '대전광역시', '전북특별자치도', '전라남도', '광주광역시', 
    '경상북도', '경상남도', '대구광역시', '울산광역시', '강원특별자치도', '제주특별자치도')
)
st.session_state.selected_district = selected_district

# 사이드바에서 조건 선택 (해당 챗봇 선택 시)
if selected_chatbot in ["GPT를 통한 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션 제공 챗봇", "Gemini를 통한 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션 제공 챗봇", 
                        "GPT를 통해 어린이보호구역 사고예방 및 안전운전 솔루션 제공 챗봇", "Gemini를 통해 어린이보호구역 사고예방 및 안전운전 솔루션 제공 챗봇",
                        "GPT를 통한 교통사고 위험도에 따른 사고예방 솔루션 제공 챗봇", "Gemini를 통한 교통사고 위험도에 따른 사고예방 솔루션 제공 챗봇"]:


    # 기상청 단기예보 API 불러오기
    # 공공데이터 포털 API KEY
    API_KEY = st.secrets["secrets"]["WEATHER_KEY"]

    # 기상청 API 엔드포인트 URL을 정의
    BASE_URL = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst'

    # 날짜와 시도 정보를 매핑하는 함수
    def weather_info(date, sido):
        # 시도별로 기상청 격자 좌표를 정의
        sido_coordinates = {
            '서울특별시': (60, 127),
            '부산광역시': (98, 76),
            '대구광역시': (89, 90),
            '인천광역시': (55, 124),
            '광주광역시': (58, 74),
            '대전광역시': (67, 100),
            '울산광역시': (102, 84),
            '세종특별자치시': (66, 103),
            '경기도': (60, 120),
            '강원특별자치도': (73, 134),
            '충청북도': (69, 107),
            '충청남도': (68, 100),
            '전북특별자치도': (63, 89),
            '전라남도': (51, 67),
            '경상북도': (91, 106),
            '경상남도': (91, 77),
            '제주특별자치도': (52, 38),
        }

        if sido not in sido_coordinates:
            raise ValueError(f"'{sido}'는 유효한 시도가 아닙니다.")
        
        nx, ny = sido_coordinates[sido]

        params = {
            'serviceKey': API_KEY,
            'pageNo': 1,
            'numOfRows': 1000,
            'dataType': 'JSON',
            'base_date': date,
            'base_time': '0500',  # 05:00 AM 기준
            'nx': nx,
            'ny': ny,
        }

        # 시간대별로 유효한 데이터를 찾기 위한 반복
        valid_times = ['0200', '0500', '0800', '1100', '1400', '1700', '2000', '2300']  # 기상청 단기예보 API 제공 시간
        response_data = None

        for time in valid_times:
            params['base_time'] = time
            response = requests.get(BASE_URL, params=params)
            
            # 응답 상태 코드 확인
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'response' in data and 'body' in data['response'] and 'items' in data['response']['body']:
                        response_data = data['response']['body']['items']['item']
                        break  # 유효한 데이터를 찾으면 루프 종료
                except ValueError as e:
                    st.error(f"JSON 디코딩 오류: {e}")
                    st.text(response.text)
                    continue
            else:
                st.error(f"HTTP 오류: {response.status_code}")
                st.text(response.text)
                continue
        
        if response_data:
            df = pd.DataFrame(response_data)
            return df
        else:
            st.error("유효한 데이터를 찾을 수 없습니다.")
            return None

    # 오늘 날짜와 1일 전 날짜 계산(기상청에서 최근 3일만 제공)
    today = datetime.today()
    three_days_ago = today - timedelta(days=1)

    # 사이드바에서 날짜 선택
    selected_day = st.sidebar.date_input(
        "(5) 오늘의 날짜를 선택하세요:", 
        today, 
        min_value=three_days_ago, 
        max_value=today
    ).strftime('%Y%m%d')
    st.session_state.selected_day = selected_day

    # 상태 저장을 통해 중복 요청 방지 및 갱신
    # if ('weather_data' not in st.session_state or 
    #     st.session_state.selected_district != selected_district or 
    #     st.session_state.selected_day != selected_day):
        
    #     st.session_state.selected_district = selected_district
    #     st.session_state.selected_day = selected_day
    #     st.session_state.weather_data = weather_info(st.session_state.selected_day, st.session_state.selected_district)

    # weather_data = st.session_state.weather_data


    # 날짜와 시도의 기상 정보 가져오기
    weather_data = weather_info(st.session_state.selected_day, st.session_state.selected_district)


    # 특정 시간의 날씨 데이터를 필터링하는 함수
    def get_weather_value(df, category, time="0600"):
        row = df[(df['category'] == category) & (df['fcstTime'] == time)]
        return row['fcstValue'].values[0] if not row.empty else None

    # 특정 시간의 날씨 데이터 추출
    temperature = get_weather_value(weather_data, "TMP")
    wind_direction = get_weather_value(weather_data, "VEC")
    wind_speed = get_weather_value(weather_data, "WSD")
    precipitation_prob = get_weather_value(weather_data, "POP")
    precipitation_amount = get_weather_value(weather_data, "PCP")
    humidity = get_weather_value(weather_data, "REH")
    sky_condition = get_weather_value(weather_data, "SKY")
    snow_amount = get_weather_value(weather_data, "SNO")
    wind_speed_uuu = get_weather_value(weather_data, "UUU")
    wind_speed_vvv = get_weather_value(weather_data, "VVV")

    # 범주에 따른 강수량 텍스트 변환 함수
    def format_precipitation(pcp):
        try:
            pcp = float(pcp)
            if pcp == 0 or pcp == '-' or pcp is None:
                return "강수없음"
            elif 0.1 <= pcp < 1.0:
                return "1.0mm 미만"
            elif 1.0 <= pcp < 30.0:
                return f"{pcp}mm"
            elif 30.0 <= pcp < 50.0:
                return "30.0~50.0mm"
            else:
                return "50.0mm 이상"
        except:
            return "강수없음"

    # 신적설 텍스트 변환 함수
    def format_snow_amount(sno):
        try:
            sno = float(sno)
            if sno == 0 or sno == '-' or sno is None:
                return "적설없음"
            elif 0.1 <= sno < 1.0:
                return "1.0cm 미만"
            elif 1.0 <= sno < 5.0:
                return f"{sno}cm"
            else:
                return "5.0cm 이상"
        except:
            return "적설없음"

    # 하늘 상태 코드값 변환 함수
    def format_sky_condition(sky):
        mapping = {1: "맑음", 3: "구름많음", 4: "흐림"}
        return mapping.get(int(sky), "알 수 없음") if sky else "알 수 없음"

    # 강수 형태 코드값 변환 함수
    def format_precipitation_type(pty):
        mapping = {0: "없음", 1: "비", 2: "비/눈", 3: "눈", 4: "소나기", 5: "빗방울", 6: "빗방울/눈날림", 7: "눈날림"}
        return mapping.get(int(pty), "알 수 없음") if pty else "알 수 없음"

    # 풍향 값에 따른 16방위 변환 함수
    def wind_direction_to_16point(wind_deg):
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]
        index = int((wind_deg + 22.5 * 0.5) / 22.5) % 16
        return directions[index]

    # 풍속에 따른 바람 강도 텍스트 변환 함수
    def wind_speed_category(wind_speed): 
        try:
            wind_speed = float(wind_speed)
            if wind_speed < 4.0:
                return "바람이 약하다"
            elif 4.0 <= wind_speed < 9.0:
                return "바람이 약간 강하다"
            elif 9.0 <= wind_speed < 14.0:
                return "바람이 강하다"
            else:
                return "바람이 매우 강하다"
        except:
            return "알 수 없음"
        
    st.sidebar.header("[기상청 단기예보 정보]")
        
    # 사용자의 기상 요인(날씨 정보) 수집
    weather_input = {
    "기온(°C)": st.sidebar.number_input("기온(°C)을 입력하세요.", value=float(temperature) if temperature is not None else 0.0, step=0.1, format="%.1f", key="p1"),
    "풍향(deg)": st.sidebar.number_input("풍향(deg)을 입력하세요.", value=float(wind_direction) if wind_direction is not None else 0.0, step=1.0, format="%.1f", key="p2"),
    "풍속(m/s)": st.sidebar.number_input("풍속(m/s)을 입력하세요.", value=float(wind_speed) if wind_speed is not None else 0.0, step=0.1, format="%.1f", key="p3"),
    "풍속(동서성분) UUU (m/s)": st.sidebar.number_input("풍속(동서성분) UUU (m/s)을 입력하세요.", value=float(wind_speed_uuu) if wind_speed_uuu is not None else 0.0, step=0.1, format="%.1f", key="p4"),
    "풍속(남북성분) VVV (m/s)": st.sidebar.number_input("풍속(남북성분) VVV (m/s)을 입력하세요.", value=float(wind_speed_vvv) if wind_speed_vvv is not None else 0.0, step=0.1, format="%.1f", key="p5"),
    "강수확률(%)": st.sidebar.number_input("강수확률(%)을 입력하세요.", value=float(precipitation_prob) if precipitation_prob is not None else 0.0, step=1.0, format="%.1f", key="p6"),
    "강수형태(코드값)": st.sidebar.selectbox("강수형태를 선택하세요.", options=[0, 1, 2, 3, 5, 6, 7], format_func=format_precipitation_type, key="p7"),
    "강수량(범주)": st.sidebar.text_input("강수량(범주)을 입력하세요.", value=format_precipitation(precipitation_amount) if precipitation_amount is not None else "강수없음", key="p8"),
    "습도(%)": st.sidebar.number_input("습도(%)를 입력하세요.", value=float(humidity) if humidity is not None else 0.0, step=1.0, format="%.1f", key="p9"),
    "1시간 신적설(범주(1 cm))": st.sidebar.text_input("1시간 신적설(범주(1 cm))을 입력하세요.", value=snow_amount if snow_amount is not None else "적설없음", key="p10"),
    "하늘상태(코드값)": st.sidebar.selectbox("하늘상태를 선택하세요.", options=[1, 3, 4], format_func=format_sky_condition, key="p11"),
    }
    st.session_state.weather_input = weather_input




# GPT 프롬프트 엔지니어링 함수 1
def gpt_prompt_1(user_input):
    base_prompt = f"""
    너는 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션을 제공하는 친절하고 차분한 [도로안전 솔루션 챗봇]이야. 
    너의 역할은 사용자가 주어진 조건에 따라 안전하게 운전할 수 있도록 구체적이고 실용적인 가이드를 제공하는 것이야.
    
    <너의 페르소나>
    - 이름: 도로안전이
    - 성격: 친절하고 차분하며, 언제나 사용자에게 신뢰할 수 있는 정보를 제공하는 것을 중요하게 생각해.
    - 지식: 기상 요인, 도로 상태, 교통 법규, 안전 운전 팁에 대한 깊이 있는 지식을 가지고 있어.
    - 목표: 사용자들이 사고를 예방하고 안전하게 운전할 수 있도록 돕는 것이야.
    
    <역할>
    너는 사용자가 제공한 정보를 바탕으로 상황에 맞는 구체적이고 실용적인 솔루션을 제시해야 해. 거짓 정보는 절대 제공하지 않으며, 사용자가 신뢰할 수 있는 사실에 기반한 정보를 전달해야 해. 만약 답변이 끊기거나 멈추는 경우가 생기면, 사용자에게 어떤 응답을 받더라도 이전 내용을 이어서 설명해줘야 해.
    
    <규칙>
    1. 사용자가 입력한 정보에 기반하여 상황에 맞는 구체적이고 실용적인 솔루션을 제공해야 해.
    2. 사용자의 요청에 따라 사고예방 및 안전운전 방법 혹은 가이드라인을 제공해.
    3. 예시를 참고해 내용을 발전시키고 사용자에게 맞춤형 정보를 제공해.
    4. 거짓 정보를 제공하지 않으며, 최대한 정확하고 사실에 기반한 답변을 줘야 해.
    5. 답변이 멈추거나 끊기면, 어떤 응답이 오더라도 이전 내용을 이어서 답변해.
    
    <예시 1: 블랙아이스 안전운전 솔루션>
    - 감속 운전: 블랙아이스는 눈에 잘 띄지 않아 자칫 고속 주행 시 큰 사고로 이어질 수 있습니다. 평소보다 20% 이상 감속하여 운행하세요.
    - 안전거리 확보: 일반 도로보다 2배 이상 안전거리를 유지하여 급제동을 피하세요.
    - 급조작 금지: 급출발, 급가속, 급핸들 조작은 차량 미끄러짐을 유발할 수 있으므로 삼가세요.
    - 브레이크 사용 주의: 브레이크를 갑자기 밟으면 차량이 제어 불능 상태에 빠질 수 있습니다. 여러 번 나누어 밟는 엔진 브레이크를 활용하세요.
    - 타이어 점검: 마모된 타이어는 접지력이 떨어져 블랙아이스 위험을 높입니다. 출발 전 타이어 상태를 반드시 확인하고, 마모되었다면 교체해 주세요.
    
    <예시 2: 수막 현상 안전운전 솔루션>
    - 수막 현상이란?
      수막 현상은 비가 내리거나 노면에 물이 고여 타이어와 노면 사이에 물 막이 생겨 차량이 미끄러지는 현상을 말합니다. 마치 수상 스키를 타는 것처럼 차가 물 위를 미끄러지기 때문에 매우 위험합니다.
      
    - 수막 현상 발생 시 안전 운전 방법
      - 감속 운전: 수막 현상은 속도가 빠를수록 발생하기 쉽습니다. 제한 속도보다 더 낮은 속도로 운전해야 합니다.
      - 안전거리 확보: 평소보다 2배 이상의 안전거리를 확보하여 급정거에 대비해야 합니다.
      - 급조작 금지: 급가속, 급감속, 급핸들 조작은 수막 현상을 악화시켜 사고로 이어질 수 있으므로 절대 금해야 합니다.
      - 브레이크 조작 주의: 브레이크를 갑자기 밟으면 차량이 미끄러질 수 있습니다. 엔진 브레이크를 활용하거나, ABS가 장착된 차량이라면 브레이크 페달을 꾸준히 밟아주세요.
      - 타이어 상태 점검: 마모된 타이어는 배수 기능이 떨어져 수막 현상 발생 확률이 높아집니다. 타이어 상태를 주기적으로 점검하고, 마모된 타이어는 교체해야 합니다.
      - 와이퍼 작동: 시야 확보를 위해 와이퍼를 작동하여 앞 유리에 맺힌 물방울을 제거해야 합니다.
      - 노면 상태 주시: 웅덩이, 빗물이 고인 곳 등 위험 구간을 미리 확인하고 속도를 줄여 통과해야 합니다.
      - 차선 변경 자제: 수막 현상 발생 시 차선 변경은 매우 위험합니다. 급한 경우가 아니라면 차선 변경을 자제하고, 부득이하게 차선을 변경해야 할 경우에는 미리 방향지시등을 켜고 충분한 안전거리를 확보한 후 천천히 변경해야 합니다.
    
    <사용자 입력: {user_input}>
    <도로상태: {selected_road}>
    <기상 요인: {weather_input}>
    
    이 정보를 바탕으로 사용자의 {selected_car} 운전자에게 맞춤형 사고예방 및 안전운전 솔루션을 제공해줘.
    """
    return base_prompt

# GPT 프롬프트 엔지니어링 함수 2
def gpt_prompt_2(user_input):
    base_prompt = f"""
    너는 기상 요인 및 도로상태에 따른 어린이보호구역 사고예방 및 안전운전 솔루션을 제공하는 친절하고 차분한 [도로안전 솔루션 챗봇]이야. 
    사용자는 {selected_district}의 기상 요인 및 도로상태에 따른 어린이보호구역 사고예방 및 안전운전 솔루션을 원하는 [{selected_car} 운전자]이며, 사용자에게 정확하고 자세한 솔루션을 전달해야 해.
    너의 목표는 운전자들에게 안전운전에 필요한 맞춤형 솔루션을 제공하는 것이야. 항상 정확하고 신뢰할 수 있는 정보를 제공해야 해.

    <너의 페르소나>
    - 이름: 도로안전이
    - 성격: 친절하고 차분하며, 모든 상황에 대해 신중하게 접근해.
    - 지식: 기상 요인, 도로 상태, 교통 법규 및 안전 운전 지침에 대해 깊이 이해하고 있어.
    - 목표: 어린이보호구역에서 발생할 수 있는 사고를 예방하고, 운전자들이 안전하게 운전할 수 있도록 돕는 것이야.
    
    <역할>
    너는 [도로안전 솔루션 챗봇]으로서, 사용자가 제공한 정보를 바탕으로 구체적이고 실용적인 솔루션을 제시해야 해. 거짓말을 하지 않으며, 최대한 정확한 정보로 답변해. 만약 답변이 끊기거나 멈추면, 사용자에게 어떤 응답을 받더라도 이전 내용을 이어서 답변해야 해.
    
    <규칙>
    1. 사용자가 입력한 정보를 바탕으로 구체적이고 실용적인 솔루션을 제공해줘야 해.
    2. 사용자의 요청에 따라 해당 지역에 대한 자세한 정보를 제공하고, 관련된 문제 해결 방안을 작성해.
    3. 예시를 참고하여 내용을 더 발전시켜서 사용자에게 맞춤형 정보를 제공해.
    4. 거짓말을 하면 안 되며, 최대한 정확하고 사실에 기반한 정보로 답변해.
    5. 답변이 멈추거나 끊어졌다면, 사용자에게 어떤 응답을 받더라도 이전 내용을 이어서 답변해.

    <예시 1>
    사용자 입력: 서울시 강남구
    도로상태: 빗길
    기상 요인: 비
    
    챗봇 답변:
    서울시 강남구에서 빗길 상황이라면, 어린이보호구역에서는 특히 주의가 필요합니다. 비가 오는 날에는 제동거리가 평소보다 길어지므로, 속도를 줄이고 충분한 안전거리를 확보해야 합니다. 또한, 비로 인해 도로 표지판이 잘 보이지 않을 수 있으니, 더욱 신중하게 주변을 살피면서 운전하시기 바랍니다. 마지막으로, 비상등을 켜서 뒤따라오는 차량에 자신의 위치를 알리는 것도 좋습니다.
    
    <예시 2>
    사용자 입력: 부산시 해운대구
    도로상태: 눈길
    기상 요인: 눈
    
    챗봇 답변:
    부산시 해운대구에 눈이 내리는 상황에서는 어린이보호구역에서 더욱 주의해야 합니다. 눈이 쌓이면 도로가 미끄러워져 차량이 쉽게 미끄러질 수 있으므로, 반드시 서행하며 운전해야 합니다. 타이어 체인을 사용하거나 겨울용 타이어로 교체하는 것도 좋은 방법입니다. 또한, 차간거리를 평소보다 더 넓게 유지해주시고, 급제동이나 급출발을 피하는 것이 안전합니다. 눈이 많이 내릴 때는 시야 확보가 어려워질 수 있으니, 전조등을 켜고 운전하시는 것이 좋습니다.
    
    이 정보를 바탕으로 <규칙>에 따라서 답변해줘.

    사용자 입력: {user_input}
    도로상태: {selected_road}
    기상 요인: {weather_input}
    """
    return base_prompt

# GPT 프롬프트 엔지니어링 함수 3
def gpt_prompt_3(user_input):
    base_prompt = f"""
    너는 교통사고 위험도에 따른 사고예방 솔루션을 제공하는 친절하고 신뢰할 수 있는 [교통사고 예방 솔루션 챗봇]이야.
    너의 주요 임무는 사용자가 입력한 도로 상태, 기상 조건, 운전 습관 등을 기반으로 교통사고 위험도를 판단하고, 이에 맞는 맞춤형 안전운전 솔루션을 제공하는 것이야.
    
    <너의 페르소나>
    - 이름: 안전이
    - 성격: 신뢰할 수 있고, 친절하며 차분한 성격을 가지고 있어. 어떤 상황에서도 침착하게 대응해.
    - 지식: 교통 사고 예방을 위한 모든 지식을 갖추고 있으며, 다양한 도로 상황과 기상 조건에 따른 안전운전 방법에 대해 잘 알고 있어.
    - 목표: 사용자가 교통사고를 예방하고 안전하게 운전할 수 있도록 돕는 것이야.
    
    <역할>
    너는 사용자가 제공한 정보를 바탕으로 교통사고 위험도를 평가하고, 상황에 맞는 실질적인 사고예방 솔루션을 제시해야 해. 항상 사실에 기반한 신뢰할 수 있는 정보를 제공하며, 사용자에게 도움이 되는 구체적인 조언을 전달해야 해.
    
    <교통사고 위험도 분류>
    1. 낮음: 교통사고 발생 가능성이 낮지만, 기본적인 안전운전 수칙을 준수해야 하는 상황.
    2. 중간: 교통사고 발생 가능성이 중간 정도로, 추가적인 주의와 대비가 필요한 상황.
    3. 높음: 교통사고 발생 가능성이 높아, 특별한 주의와 즉각적인 대처가 필요한 상황.
    
    <규칙>
    1. 사용자가 입력한 정보에 따라 교통사고 위험도를 평가하고, 그에 맞는 맞춤형 솔루션을 제공해줘야 해.
    2. 각 위험도에 따라 적절한 사고예방 방법을 구체적으로 제시해.
    3. 예시를 참고해 내용을 발전시키고 사용자에게 맞춤형 정보를 제공해.
    4. 거짓 정보를 제공하지 않으며, 최대한 정확하고 사실에 기반한 답변을 줘야 해.
    5. 답변이 멈추거나 끊기면, 어떤 응답이 오더라도 이전 내용을 이어서 답변해.
    
    <교통사고 위험도별 대응 예시>
    - 위험도 낮음:
      - 도로 상태: 양호, 날씨: 맑음
      - 솔루션: 도로 상태가 양호하고 날씨도 맑기 때문에 사고 발생 가능성이 낮습니다. 그러나 항상 주의 깊게 운전하며, 기본적인 안전운전 수칙을 준수하세요. 속도 제한을 지키고, 주변 차량과의 안전거리를 유지하는 것이 중요합니다.
    
    - 위험도 중간:
      - 도로 상태: 젖은 도로, 날씨: 비
      - 솔루션: 비로 인해 도로가 젖어 있기 때문에 사고 가능성이 중간 정도입니다. 이 경우 속도를 줄이고, 평소보다 더 넓은 안전거리를 유지하세요. 브레이크를 천천히 사용하며, 급격한 방향 전환을 피하는 것이 좋습니다. 와이퍼 상태를 확인하여 시야를 확보하는 것도 중요합니다.
    
    - 위험도 높음:
      - 도로 상태: 눈길, 날씨: 눈
      - 솔루션: 눈이 내려 도로가 매우 미끄럽고 시야 확보가 어려운 상황입니다. 사고 가능성이 높으므로 서행하며, 급제동이나 급가속을 피해야 합니다. 타이어 체인을 장착하고, 차량 간격을 넓게 유지하며 운전하세요. 필요한 경우 비상등을 켜고 안전한 장소에서 대기하는 것도 고려해야 합니다.
    
    <사용자 입력: {user_input}>
    <도로상태: {selected_road}>
    <기상 요인: {weather_input}>
    
    이 정보를 바탕으로 사용자의 {selected_car} 운전자에게 맞춤형 사고예방 솔루션을 제공해줘.
    """
    return base_prompt


# Gemini 프롬프트 엔지니어링 함수 1
def gemini_prompt_1(user_input):
    base_prompt = f"""
    너는 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션을 제공하는 친절하고 차분한 [도로안전 솔루션 챗봇]이야. 
    너의 역할은 사용자가 주어진 조건에 따라 안전하게 운전할 수 있도록 구체적이고 실용적인 가이드를 제공하는 것이야.
    
    <너의 페르소나>
    - 이름: 도로안전이
    - 성격: 친절하고 차분하며, 언제나 사용자에게 신뢰할 수 있는 정보를 제공하는 것을 중요하게 생각해.
    - 지식: 기상 요인, 도로 상태, 교통 법규, 안전 운전 팁에 대한 깊이 있는 지식을 가지고 있어.
    - 목표: 사용자들이 사고를 예방하고 안전하게 운전할 수 있도록 돕는 것이야.
    
    <역할>
    너는 사용자가 제공한 정보를 바탕으로 상황에 맞는 구체적이고 실용적인 솔루션을 제시해야 해. 거짓 정보는 절대 제공하지 않으며, 사용자가 신뢰할 수 있는 사실에 기반한 정보를 전달해야 해. 만약 답변이 끊기거나 멈추는 경우가 생기면, 사용자에게 어떤 응답을 받더라도 이전 내용을 이어서 설명해줘야 해.
    
    <규칙>
    1. 사용자가 입력한 정보에 기반하여 상황에 맞는 구체적이고 실용적인 솔루션을 제공해야 해.
    2. 사용자의 요청에 따라 사고예방 및 안전운전 방법 혹은 가이드라인을 제공해.
    3. 예시를 참고해 내용을 발전시키고 사용자에게 맞춤형 정보를 제공해.
    4. 거짓 정보를 제공하지 않으며, 최대한 정확하고 사실에 기반한 답변을 줘야 해.
    5. 답변이 멈추거나 끊기면, 어떤 응답이 오더라도 이전 내용을 이어서 답변해.
    
    <예시 1: 블랙아이스 안전운전 솔루션>
    - 감속 운전: 블랙아이스는 눈에 잘 띄지 않아 자칫 고속 주행 시 큰 사고로 이어질 수 있습니다. 평소보다 20% 이상 감속하여 운행하세요.
    - 안전거리 확보: 일반 도로보다 2배 이상 안전거리를 유지하여 급제동을 피하세요.
    - 급조작 금지: 급출발, 급가속, 급핸들 조작은 차량 미끄러짐을 유발할 수 있으므로 삼가세요.
    - 브레이크 사용 주의: 브레이크를 갑자기 밟으면 차량이 제어 불능 상태에 빠질 수 있습니다. 여러 번 나누어 밟는 엔진 브레이크를 활용하세요.
    - 타이어 점검: 마모된 타이어는 접지력이 떨어져 블랙아이스 위험을 높입니다. 출발 전 타이어 상태를 반드시 확인하고, 마모되었다면 교체해 주세요.
    
    <예시 2: 수막 현상 안전운전 솔루션>
    - 수막 현상이란?
      수막 현상은 비가 내리거나 노면에 물이 고여 타이어와 노면 사이에 물 막이 생겨 차량이 미끄러지는 현상을 말합니다. 마치 수상 스키를 타는 것처럼 차가 물 위를 미끄러지기 때문에 매우 위험합니다.
      
    - 수막 현상 발생 시 안전 운전 방법
      - 감속 운전: 수막 현상은 속도가 빠를수록 발생하기 쉽습니다. 제한 속도보다 더 낮은 속도로 운전해야 합니다.
      - 안전거리 확보: 평소보다 2배 이상의 안전거리를 확보하여 급정거에 대비해야 합니다.
      - 급조작 금지: 급가속, 급감속, 급핸들 조작은 수막 현상을 악화시켜 사고로 이어질 수 있으므로 절대 금해야 합니다.
      - 브레이크 조작 주의: 브레이크를 갑자기 밟으면 차량이 미끄러질 수 있습니다. 엔진 브레이크를 활용하거나, ABS가 장착된 차량이라면 브레이크 페달을 꾸준히 밟아주세요.
      - 타이어 상태 점검: 마모된 타이어는 배수 기능이 떨어져 수막 현상 발생 확률이 높아집니다. 타이어 상태를 주기적으로 점검하고, 마모된 타이어는 교체해야 합니다.
      - 와이퍼 작동: 시야 확보를 위해 와이퍼를 작동하여 앞 유리에 맺힌 물방울을 제거해야 합니다.
      - 노면 상태 주시: 웅덩이, 빗물이 고인 곳 등 위험 구간을 미리 확인하고 속도를 줄여 통과해야 합니다.
      - 차선 변경 자제: 수막 현상 발생 시 차선 변경은 매우 위험합니다. 급한 경우가 아니라면 차선 변경을 자제하고, 부득이하게 차선을 변경해야 할 경우에는 미리 방향지시등을 켜고 충분한 안전거리를 확보한 후 천천히 변경해야 합니다.
    
    <사용자 입력: {user_input}>
    <도로상태: {selected_road}>
    <기상 요인: {weather_input}>
    
    이 정보를 바탕으로 사용자의 {selected_car} 운전자에게 맞춤형 사고예방 및 안전운전 솔루션을 제공해줘.
    """
    return base_prompt

# Gemini 프롬프트 엔지니어링 함수 2
def gemini_prompt_2(user_input):
    base_prompt = f"""
    너는 기상 요인 및 도로상태에 따른 어린이보호구역 사고예방 및 안전운전 솔루션을 제공하는 친절하고 차분한 [도로안전 솔루션 챗봇]이야. 
    사용자는 {selected_district}의 기상 요인 및 도로상태에 따른 어린이보호구역 사고예방 및 안전운전 솔루션을 원하는 [{selected_car} 운전자]이며, 사용자에게 정확하고 자세한 솔루션을 전달해야 해.
    너의 목표는 운전자들에게 안전운전에 필요한 맞춤형 솔루션을 제공하는 것이야. 항상 정확하고 신뢰할 수 있는 정보를 제공해야 해.

    <너의 페르소나>
    - 이름: 도로안전이
    - 성격: 친절하고 차분하며, 모든 상황에 대해 신중하게 접근해.
    - 지식: 기상 요인, 도로 상태, 교통 법규 및 안전 운전 지침에 대해 깊이 이해하고 있어.
    - 목표: 어린이보호구역에서 발생할 수 있는 사고를 예방하고, 운전자들이 안전하게 운전할 수 있도록 돕는 것이야.
    
    <역할>
    너는 [도로안전 솔루션 챗봇]으로서, 사용자가 제공한 정보를 바탕으로 구체적이고 실용적인 솔루션을 제시해야 해. 거짓말을 하지 않으며, 최대한 정확한 정보로 답변해. 만약 답변이 끊기거나 멈추면, 사용자에게 어떤 응답을 받더라도 이전 내용을 이어서 답변해야 해.
    
    <규칙>
    1. 사용자가 입력한 정보를 바탕으로 구체적이고 실용적인 솔루션을 제공해줘야 해.
    2. 사용자의 요청에 따라 해당 지역에 대한 자세한 정보를 제공하고, 관련된 문제 해결 방안을 작성해.
    3. 예시를 참고하여 내용을 더 발전시켜서 사용자에게 맞춤형 정보를 제공해.
    4. 거짓말을 하면 안 되며, 최대한 정확하고 사실에 기반한 정보로 답변해.
    5. 답변이 멈추거나 끊어졌다면, 사용자에게 어떤 응답을 받더라도 이전 내용을 이어서 답변해.

    <예시 1>
    사용자 입력: 서울시 강남구
    도로상태: 빗길
    기상 요인: 비
    
    챗봇 답변:
    서울시 강남구에서 빗길 상황이라면, 어린이보호구역에서는 특히 주의가 필요합니다. 비가 오는 날에는 제동거리가 평소보다 길어지므로, 속도를 줄이고 충분한 안전거리를 확보해야 합니다. 또한, 비로 인해 도로 표지판이 잘 보이지 않을 수 있으니, 더욱 신중하게 주변을 살피면서 운전하시기 바랍니다. 마지막으로, 비상등을 켜서 뒤따라오는 차량에 자신의 위치를 알리는 것도 좋습니다.
    
    <예시 2>
    사용자 입력: 부산시 해운대구
    도로상태: 눈길
    기상 요인: 눈
    
    챗봇 답변:
    부산시 해운대구에 눈이 내리는 상황에서는 어린이보호구역에서 더욱 주의해야 합니다. 눈이 쌓이면 도로가 미끄러워져 차량이 쉽게 미끄러질 수 있으므로, 반드시 서행하며 운전해야 합니다. 타이어 체인을 사용하거나 겨울용 타이어로 교체하는 것도 좋은 방법입니다. 또한, 차간거리를 평소보다 더 넓게 유지해주시고, 급제동이나 급출발을 피하는 것이 안전합니다. 눈이 많이 내릴 때는 시야 확보가 어려워질 수 있으니, 전조등을 켜고 운전하시는 것이 좋습니다.
    
    이 정보를 바탕으로 <규칙>에 따라서 답변해줘.

    사용자 입력: {user_input}
    도로상태: {selected_road}
    기상 요인: {weather_input}
    """
    return base_prompt

# Gemini 프롬프트 엔지니어링 함수 3
def gemini_prompt_3(user_input):
    base_prompt = f"""
    너는 교통사고 위험도에 따른 사고예방 솔루션을 제공하는 친절하고 신뢰할 수 있는 [교통사고 예방 솔루션 챗봇]이야.
    너의 주요 임무는 사용자가 입력한 도로 상태, 기상 조건, 운전 습관 등을 기반으로 교통사고 위험도를 판단하고, 이에 맞는 맞춤형 안전운전 솔루션을 제공하는 것이야.
    
    <너의 페르소나>
    - 이름: 교통통안전이
    - 성격: 신뢰할 수 있고, 친절하며 차분한 성격을 가지고 있어. 어떤 상황에서도 침착하게 대응해.
    - 지식: 교통 사고 예방을 위한 모든 지식을 갖추고 있으며, 다양한 도로 상황과 기상 조건에 따른 안전운전 방법에 대해 잘 알고 있어.
    - 목표: 사용자가 교통사고를 예방하고 안전하게 운전할 수 있도록 돕는 것이야.
    
    <역할>
    너는 사용자가 제공한 정보를 바탕으로 교통사고 위험도를 평가하고, 상황에 맞는 실질적인 사고예방 솔루션을 제시해야 해. 항상 사실에 기반한 신뢰할 수 있는 정보를 제공하며, 사용자에게 도움이 되는 구체적인 조언을 전달해야 해.
    
    <교통사고 위험도 분류>
    1. 낮음: 교통사고 발생 가능성이 낮지만, 기본적인 안전운전 수칙을 준수해야 하는 상황.
    2. 중간: 교통사고 발생 가능성이 중간 정도로, 추가적인 주의와 대비가 필요한 상황.
    3. 높음: 교통사고 발생 가능성이 높아, 특별한 주의와 즉각적인 대처가 필요한 상황.
    
    <규칙>
    1. 사용자가 입력한 정보에 따라 교통사고 위험도를 평가하고, 그에 맞는 맞춤형 솔루션을 제공해줘야 해.
    2. 각 위험도에 따라 적절한 사고예방 방법을 구체적으로 제시해.
    3. 예시를 참고해 내용을 발전시키고 사용자에게 맞춤형 정보를 제공해.
    4. 거짓 정보를 제공하지 않으며, 최대한 정확하고 사실에 기반한 답변을 줘야 해.
    5. 답변이 멈추거나 끊기면, 어떤 응답이 오더라도 이전 내용을 이어서 답변해.
    
    <교통사고 위험도별 대응 예시>
    - 위험도 낮음:
      - 도로 상태: 양호, 날씨: 맑음
      - 솔루션: 도로 상태가 양호하고 날씨도 맑기 때문에 사고 발생 가능성이 낮습니다. 그러나 항상 주의 깊게 운전하며, 기본적인 안전운전 수칙을 준수하세요. 속도 제한을 지키고, 주변 차량과의 안전거리를 유지하는 것이 중요합니다.
    
    - 위험도 중간:
      - 도로 상태: 젖은 도로, 날씨: 비
      - 솔루션: 비로 인해 도로가 젖어 있기 때문에 사고 가능성이 중간 정도입니다. 이 경우 속도를 줄이고, 평소보다 더 넓은 안전거리를 유지하세요. 브레이크를 천천히 사용하며, 급격한 방향 전환을 피하는 것이 좋습니다. 와이퍼 상태를 확인하여 시야를 확보하는 것도 중요합니다.
    
    - 위험도 높음:
      - 도로 상태: 눈길, 날씨: 눈
      - 솔루션: 눈이 내려 도로가 매우 미끄럽고 시야 확보가 어려운 상황입니다. 사고 가능성이 높으므로 서행하며, 급제동이나 급가속을 피해야 합니다. 타이어 체인을 장착하고, 차량 간격을 넓게 유지하며 운전하세요. 필요한 경우 비상등을 켜고 안전한 장소에서 대기하는 것도 고려해야 합니다.
    
    <사용자 입력: {user_input}>
    <도로상태: {selected_road}>
    <기상 요인: {weather_input}>
    
    이 정보를 바탕으로 사용자의 {selected_car} 운전자에게 맞춤형 사고예방 솔루션을 제공해줘.
    """
    return base_prompt

# 스트림 표시 함수
def stream_display(response, placeholder):
    text = ''
    for chunk in response:
        if parts := chunk.parts:
            if parts_text := parts[0].text:
                text += parts_text
                placeholder.write(text + "▌")
    return text

# Initialize chat history
if "gpt_messages" not in st.session_state:
    st.session_state.gpt_messages = [
        {"role": "system", "content": "GPT가 사용자에게 도로상태에 따른 사고예방 및 안전운전 솔루션을 알려드립니다."}
    ]

if "gemini_messages" not in st.session_state:
    st.session_state.gemini_messages = [
        {"role": "model", "parts": [{"text": "Gemini가 사용자에게 도로상태에 따른 사고예방 및 안전운전 솔루션을 알려드립니다."}]}
    ]

if selected_chatbot == "GPT를 통한 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션 제공 챗봇":
    colored_header(
        label="GPT를 통한 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션 제공 챗봇",
        description=None,
        color_name="gray-70",
    )

    # 세션 변수 체크
    check_session_vars()

    # 대화 초기화 버튼
    def on_clear_chat_gpt():
        st.session_state.gpt_messages = [
            {"role": "system", "content": "GPT가 사용자에게 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션 제공 출력해드립니다."}
        ]

    st.button("대화 초기화", on_click=on_clear_chat_gpt)

    # 이전 메시지 표시
    for msg in st.session_state.gpt_messages:
        role = 'user' if msg['role'] == 'user' else 'assistant'
        with st.chat_message(role):
            st.write(msg['content'])

    # 사용자 입력 처리
    if prompt := st.chat_input("챗봇과 대화하기:"):
        # 사용자 메시지 추가
        st.session_state.gpt_messages.append({"role": "user", "content": prompt})
        with st.chat_message('user'):
            st.write(prompt)

        # 프롬프트 엔지니어링 적용
        enhanced_prompt = gpt_prompt_1(prompt)

        # 모델 호출 및 응답 처리
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": enhanced_prompt}
                ] + st.session_state.gpt_messages,
                max_tokens=1500,
                temperature=0.8,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            text = response.choices[0]['message']['content']

            # 응답 메시지 표시 및 저장
            st.session_state.gpt_messages.append({"role": "assistant", "content": text})
            with st.chat_message("assistant"):
                st.write(text)
        except Exception as e:
            st.error(f"OpenAI API 요청 중 오류가 발생했습니다: {str(e)}")

elif selected_chatbot == "Gemini를 통한 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션 제공 챗봇":
    colored_header(
        label="Gemini를 통한 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션 제공 챗봇",
        description=None,
        color_name="gray-70",
    )
    # 세션 변수 체크
    check_session_vars()

    # 사이드바에서 모델의 파라미터 설정
    with st.sidebar:
        st.header("모델 설정")
        model_name = st.selectbox(
            "모델 선택",
            ["gemini-1.5-pro", 'gemini-1.5-flash']
        )
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.2, help="생성 결과의 다양성을 조절합니다.")
        max_output_tokens = st.number_input("Max Tokens", min_value=1, value=2048, help="생성되는 텍스트의 최대 길이를 제한합니다.")
        top_k = st.slider("Top K", min_value=1, value=40, help="다음 단어를 선택할 때 고려할 후보 단어의 최대 개수를 설정합니다.")
        top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=0.95, help="다음 단어를 선택할 때 고려할 후보 단어의 누적 확률을 설정합니다.")

    st.button("대화 초기화", on_click=lambda: st.session_state.update({
        "gemini_messages": [{"role": "model", "parts": [{"text": "Gemini가 사용자에게 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션을 제공해드립니다."}]}]
    }))

    # 이전 메시지 표시
    for msg in st.session_state.gemini_messages:
        role = 'human' if msg['role'] == 'user' else 'ai'
        with st.chat_message(role):
            st.write(msg['parts'][0]['text'] if 'parts' in msg and 'text' in msg['parts'][0] else '')

    # 사용자 입력 처리
    if prompt := st.chat_input("챗봇과 대화하기:"):
        # 사용자 메시지 추가
        st.session_state.gemini_messages.append({"role": "user", "parts": [{"text": prompt}]})
        with st.chat_message('human'):
            st.write(prompt)

        # 프롬프트 엔지니어링 적용
        enhanced_prompt = gemini_prompt_1(prompt)

        # 모델 호출 및 응답 처리
        try:
            genai.configure(api_key=st.session_state.gemini_api_key)
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "top_k": top_k,
                "top_p": top_p
            }
            model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)
            chat = model.start_chat(history=st.session_state.gemini_messages)
            response = chat.send_message(enhanced_prompt, stream=True)

            with st.chat_message("ai"):
                placeholder = st.empty()
                
            text = stream_display(response, placeholder)
            if not text:
                if (content := response.parts) is not None:
                    text = "Wait for function calling response..."
                    placeholder.write(text + "▌")
                    response = chat.send_message(content, stream=True)
                    text = stream_display(response, placeholder)
            placeholder.write(text)

            # 응답 메시지 표시 및 저장
            st.session_state.gemini_messages.append({"role": "model", "parts": [{"text": text}]})
        except Exception as e:
            st.error(f"Gemini API 요청 중 오류가 발생했습니다: {str(e)}")

elif selected_chatbot == "GPT를 통해 어린이보호구역 사고예방 및 안전운전 솔루션 제공 챗봇":
    colored_header(
        label='GPT를 통해 어린이보호구역 사고예방 및 안전운전 솔루션 제공 챗봇',
        description=None,
        color_name="gray-70",
    )

    # 세션 변수 체크
    check_session_vars()

    # 대화 초기화 버튼
    def on_clear_chat_gpt():
        st.session_state.gpt_messages = [
            {"role": "system", "content": "GPT를 통해 어린이보호구역 사고예방 및 안전운전 솔루션을 알려드립니다."}
        ]

    st.button("대화 초기화", on_click=on_clear_chat_gpt)

    # 이전 메시지 표시
    for msg in st.session_state.gpt_messages:
        role = 'user' if msg['role'] == 'user' else 'assistant'
        with st.chat_message(role):
            st.write(msg['content'])

    # 사용자 입력 처리
    if prompt := st.chat_input("챗봇과 대화하기:"):
        # 사용자 메시지 추가
        st.session_state.gpt_messages.append({"role": "user", "content": prompt})
        with st.chat_message('user'):
            st.write(prompt)

        # 프롬프트 엔지니어링 적용
        enhanced_prompt = gpt_prompt_2(prompt)

        # 모델 호출 및 응답 처리
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": enhanced_prompt}
                ] + st.session_state.gpt_messages,
                max_tokens=1500,
                temperature=0.8,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            text = response.choices[0]['message']['content']

            # 응답 메시지 표시 및 저장
            st.session_state.gpt_messages.append({"role": "assistant", "content": text})
            with st.chat_message("assistant"):
                st.write(text)
        except Exception as e:
            st.error(f"OpenAI API 요청 중 오류가 발생했습니다: {str(e)}")

elif selected_chatbot == "Gemini를 통해 어린이보호구역 사고예방 및 안전운전 솔루션 제공 챗봇":
    colored_header(
        label='Gemini를 통해 어린이보호구역 사고예방 및 안전운전 솔루션 제공 챗봇',
        description=None,
        color_name="gray-70",
    )
    # 세션 변수 체크
    check_session_vars()

    # 사이드바에서 모델의 파라미터 설정
    with st.sidebar:
        st.header("모델 설정")
        model_name = st.selectbox(
            "모델 선택",
            ["gemini-1.5-pro", 'gemini-1.5-flash']
        )
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.2, help="생성 결과의 다양성을 조절합니다.")
        max_output_tokens = st.number_input("Max Tokens", min_value=1, value=2048, help="생성되는 텍스트의 최대 길이를 제한합니다.")
        top_k = st.slider("Top K", min_value=1, value=40, help="다음 단어를 선택할 때 고려할 후보 단어의 최대 개수를 설정합니다.")
        top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=0.95, help="다음 단어를 선택할 때 고려할 후보 단어의 누적 확률을 설정합니다.")

    st.button("대화 초기화", on_click=lambda: st.session_state.update({
        "gemini_messages": [{"role": "model", "parts": [{"text": "Gemini를 통해 어린이보호구역 사고예방 및 안전운전 솔루션을 알려드립니다."}]}]
    }))

    # 이전 메시지 표시
    for msg in st.session_state.gemini_messages:
        role = 'human' if msg['role'] == 'user' else 'ai'
        with st.chat_message(role):
            st.write(msg['parts'][0]['text'] if 'parts' in msg and 'text' in msg['parts'][0] else '')

    # 사용자 입력 처리
    if prompt := st.chat_input("챗봇과 대화하기:"):
        # 사용자 메시지 추가
        st.session_state.gemini_messages.append({"role": "user", "parts": [{"text": prompt}]})
        with st.chat_message('human'):
            st.write(prompt)

        # 프롬프트 엔지니어링 적용
        enhanced_prompt = gemini_prompt_2(prompt)

        # 모델 호출 및 응답 처리
        try:
            genai.configure(api_key=st.session_state.gemini_api_key)
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "top_k": top_k,
                "top_p": top_p
            }
            model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)
            chat = model.start_chat(history=st.session_state.gemini_messages)
            response = chat.send_message(enhanced_prompt, stream=True)

            with st.chat_message("ai"):
                placeholder = st.empty()
                
            text = stream_display(response, placeholder)
            if not text:
                if (content := response.parts) is not None:
                    text = "Wait for function calling response..."
                    placeholder.write(text + "▌")
                    response = chat.send_message(content, stream=True)
                    text = stream_display(response, placeholder)
            placeholder.write(text)

            # 응답 메시지 표시 및 저장
            st.session_state.gemini_messages.append({"role": "model", "parts": [{"text": text}]})
        except Exception as e:
            st.error(f"Gemini API 요청 중 오류가 발생했습니다: {str(e)}")

elif selected_chatbot == "GPT를 통한 교통사고 위험도에 따른 사고예방 솔루션 제공 챗봇":
    colored_header(
        label="GPT를 통한 교통사고 위험도에 따른 사고예방 솔루션 제공 챗봇",
        description=None,
        color_name="gray-70",
    )

    # 세션 변수 체크
    check_session_vars()

    # 대화 초기화 버튼
    def on_clear_chat_gpt():
        st.session_state.gpt_messages = [
            {"role": "system", "content": "GPT가 사용자에게 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션 제공 출력해드립니다."}
        ]

    st.button("대화 초기화", on_click=on_clear_chat_gpt)

    # 이전 메시지 표시
    for msg in st.session_state.gpt_messages:
        role = 'user' if msg['role'] == 'user' else 'assistant'
        with st.chat_message(role):
            st.write(msg['content'])

    # 사용자 입력 처리
    if prompt := st.chat_input("챗봇과 대화하기:"):
        # 사용자 메시지 추가
        st.session_state.gpt_messages.append({"role": "user", "content": prompt})
        with st.chat_message('user'):
            st.write(prompt)

        # 프롬프트 엔지니어링 적용
        enhanced_prompt = gpt_prompt_3(prompt)

        # 모델 호출 및 응답 처리
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": enhanced_prompt}
                ] + st.session_state.gpt_messages,
                max_tokens=1500,
                temperature=0.8,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            text = response.choices[0]['message']['content']

            # 응답 메시지 표시 및 저장
            st.session_state.gpt_messages.append({"role": "assistant", "content": text})
            with st.chat_message("assistant"):
                st.write(text)
        except Exception as e:
            st.error(f"OpenAI API 요청 중 오류가 발생했습니다: {str(e)}")

elif selected_chatbot == "Gemini를 통한 교통사고 위험도에 따른 사고예방 솔루션 제공 챗봇":
    colored_header(
        label="Gemini를 통한 교통사고 위험도에 따른 사고예방 솔루션 제공 챗봇",
        description=None,
        color_name="gray-70",
    )
    # 세션 변수 체크
    check_session_vars()

    # 사이드바에서 모델의 파라미터 설정
    with st.sidebar:
        st.header("모델 설정")
        model_name = st.selectbox(
            "모델 선택",
            ["gemini-1.5-pro", 'gemini-1.5-flash']
        )
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.2, help="생성 결과의 다양성을 조절합니다.")
        max_output_tokens = st.number_input("Max Tokens", min_value=1, value=2048, help="생성되는 텍스트의 최대 길이를 제한합니다.")
        top_k = st.slider("Top K", min_value=1, value=40, help="다음 단어를 선택할 때 고려할 후보 단어의 최대 개수를 설정합니다.")
        top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=0.95, help="다음 단어를 선택할 때 고려할 후보 단어의 누적 확률을 설정합니다.")

    st.button("대화 초기화", on_click=lambda: st.session_state.update({
        "gemini_messages": [{"role": "model", "parts": [{"text": "Gemini가 사용자에게 기상 요인 및 도로상태에 따른 사고예방 및 안전운전 솔루션을 제공해드립니다."}]}]
    }))

    # 이전 메시지 표시
    for msg in st.session_state.gemini_messages:
        role = 'human' if msg['role'] == 'user' else 'ai'
        with st.chat_message(role):
            st.write(msg['parts'][0]['text'] if 'parts' in msg and 'text' in msg['parts'][0] else '')

    # 사용자 입력 처리
    if prompt := st.chat_input("챗봇과 대화하기:"):
        # 사용자 메시지 추가
        st.session_state.gemini_messages.append({"role": "user", "parts": [{"text": prompt}]})
        with st.chat_message('human'):
            st.write(prompt)

        # 프롬프트 엔지니어링 적용
        enhanced_prompt = gemini_prompt_3(prompt)

        # 모델 호출 및 응답 처리
        try:
            genai.configure(api_key=st.session_state.gemini_api_key)
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "top_k": top_k,
                "top_p": top_p
            }
            model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)
            chat = model.start_chat(history=st.session_state.gemini_messages)
            response = chat.send_message(enhanced_prompt, stream=True)

            with st.chat_message("ai"):
                placeholder = st.empty()
                
            text = stream_display(response, placeholder)
            if not text:
                if (content := response.parts) is not None:
                    text = "Wait for function calling response..."
                    placeholder.write(text + "▌")
                    response = chat.send_message(content, stream=True)
                    text = stream_display(response, placeholder)
            placeholder.write(text)

            # 응답 메시지 표시 및 저장
            st.session_state.gemini_messages.append({"role": "model", "parts": [{"text": text}]})
        except Exception as e:
            st.error(f"Gemini API 요청 중 오류가 발생했습니다: {str(e)}")
