from datetime import date, datetime, timedelta, timezone
from icalendar import Calendar, Event
from zoneinfo import ZoneInfo
from typing import Union, Any
import hashlib

class SchoolICS:
    def __init__(self, school_name: str, school_id: str, author_name: str, author_program: str, cal_name: str, timezone: ZoneInfo, oneday_allday: bool = True) -> None:
        if not school_id.isalnum():
            raise ValueError("'school_id' must be alphanumeric value")

        self.school_name = school_name
        self.school_id = school_id
        self.calendar_name = cal_name
        self.author = {
            "name": author_name,
            "program": author_program
        }
        self.tz = timezone
        # self.oneday_allday = oneday_allday # 하루짜리 이벤트를 '하루 종일'로 표시할지, 0시 - 0시 이벤트로 표시할지 결정
        # 1. 하루 종일:
        # 캘린더에 꽉찬 네모로 표시
        # 2. 0시 - 0시:
        # 캘린더에 '| 일정명' 처럼 얇은 바로 표시

        self.events = []
        self.calendar = Calendar()

        self.calendar.add("version", "2.0") # 버전
        self.calendar.add("prodid", f"-//{author_name}//{author_program}//KO") # 작성자
        self.calendar.add("calscale", "GREGORIAN") # 그레고리력
        self.calendar.add("method", "PUBLISH") # 구독용 공개 캘린더
        self.calendar.add("x-wr-calname", cal_name) # 캘린더 표시 이름
        self.calendar.add("x-wr-timezone", "Asia/Seoul") # 시간대

    def parse_grade(
        self,
        grade_pattern: str
    ) -> tuple[int, ...]:
        return tuple(
            grade for grade, bit in enumerate(grade_pattern, start=1) if bit == '1' # grade 인덱스(학년)와 실제 비트값(0, 1) 비교하면서 반복, bit가 1이라면 튜플에 (학년) 포함
        )

    def add_event(
        self,
        event_name: str,
        start_date: date,
        end_date: date = None,
        event_description: str = None,
        target_grades: tuple = (1, 2, 3), # 기본값: 전체 학년
        holiday: bool = False
    ) -> None:
        if not end_date: # 종료일이 입력되지 않으면 (= 하루짜리 일정)
            end_date = start_date + timedelta(days=1) # 종료일을 다음날로 지정 (단, 실제 캘린더에서는 하루짜리 일정임.)
        else: # 2일 이상의 일정이라면
            end_date += timedelta(days=1) # 종료일을 (실제 종료일 + 1)일로 변경, ics는 예를 들어 7/3 - 7/5 일정을 만들고 싶으면 시작일을 7/3, 종료일을 7/6으로 설정해야 캘린더에서 제대로 표시됨.

        """
        if self.tz: # 사용자가 캘린더의 시간대를 설정해놓았다면
            start_date.replace(tzinfo=self.tz) # 시간대 바꾸기
            end_date.replace(tzinfo=self.tz) # 시간대 바꾸기
        
        if end_date < start_date: # 시작이 끝보다 빠르면
            raise ValueError("'end_date' cannot be earlier than 'start_date'")

        폐기: 원래는 datetime을 써서 필요했지만 date 객체로 바꾸고 필요없어짐
        """


        event = Event.new( # 이벤트 생성
            uid=f"jahs-{hashlib.sha256(f"{event_name}-{start_date.strftime("%y%m%d")}".encode()).hexdigest()[:12]}@local", # uid 형식: 'jahs-(일정이름-날짜 sha256 해시의 앞 12글자)@local'
            stamp=datetime.now(timezone.utc),
            start=start_date, # 시작 날짜
            end=end_date, # 종료 날짜
            summary=event_name, # 일정 이름
        )
        event.add(
            "x-grade", "".join(
                '1' if grade in target_grades else '0' for grade in range(1, 3+1) # 대상 학년 안에 n학년이 있으면 1, 없으면 0
            )
        )

        self.calendar.add_component(event) # 캘린더에 일정 추가

    def export_ics(self,
        target_grades: tuple = (1, 2, 3), # 기본값: 전체 학년
        output_path: str = None, # 기본값: 문자열만 전달 (파일 쓰지 않음)
        return_bytes: bool = False
    ):
        ics_dt = self.calendar.to_ical() # 일단 캘린더 ics로 변환

        if target_grades != (1, 2, 3): # 특정 학년 일정만 뽑으려 한다면
            filtered_cal = self.calendar.copy() # 전체 캘린더 복사
            filtered_cal.events.clear() # 이벤트만 삭제

            filter_vevent = lambda x: bool(set(target_grades) & set(self.parse_grade(x.get("x-grade", "111")))) # 대상 학년과 캘린더의 학년의 교집합(겹치는 부분)이 있는지 검사하는 람다함수, 만약 x-grade 항목이 없으면 111 (전 학년)으로 통과시키기
            # 단, set(...) & set(...) 를 반환하면 교집합을 반환하니 bool로 변환 후 반환

            for comp in self.calendar.walk(select=filter_vevent):
                filtered_cal.add_component(comp)
        
            ics_dt = filtered_cal.to_ical() # 바꾸기

        if output_path: # ics 파일 경로를 지정해놓았으면
            with open(output_path, "wb") as ics_file: # to_ical()은 기본적으로 bytes 형식으로 반환함
                ics_file.write(ics_dt) # ics 파일 생성해주기
        
        if return_bytes:
            return ics_dt # bytes 그대로 반환
        else:
            return ics_dt.decode("utf-8") # ics를 문자열로 변환 및 반환

class MenuICS:
    def __init__(self, author_name: str, author_program: str, cal_name: str, timezone: ZoneInfo) -> None:
        self.calendar_name = cal_name
        self.author = {
            "name": author_name,
            "program": author_program
        }
        self.tz = timezone

        self.events = []
        self.calendar = Calendar()

        self.calendar.add("version", "2.0") # 버전
        self.calendar.add("prodid", f"-//{author_name}//{author_program}//KO") # 작성자
        self.calendar.add("calscale", "GREGORIAN") # 그레고리력
        self.calendar.add("method", "PUBLISH") # 구독용 공개 캘린더
        self.calendar.add("x-wr-calname", cal_name) # 캘린더 표시 이름
        self.calendar.add("x-wr-timezone", "Asia/Seoul") # 시간대

    def add_menu(
        self,
        menu_name: Union[str, list],
        menu_date: datetime,
        sep: str = ","
    ):
        if self.tz: # 사용자가 캘린더의 시간대를 설정해놓았다면
            menu_date.replace(tzinfo=self.tz) # 시간대 바꾸기

        if not menu_name:
            raise ValueError("'menu_name' cannot be None")

        if isinstance(menu_name, str):
            menu_name = menu_name.strip().split(sep)

        event = Event.new( # 이벤트 생성
            uid=f"jahs-{hashlib.sha256(f"{menu_name}-{menu_date.strftime("%y%m%d")}".encode()).hexdigest()[:12]}@local", # uid 형식: 'jahs-(일정이름-날짜 sha256 해시의 앞 12글자)@local'
            stamp=datetime.now(timezone.utc),
            start=menu_date, # 시작 날짜
            end=menu_date + timedelta(days=1), # 종료 날짜 (하루짜리라서 x+1일)
            summary=menu_name, # 일정 이름
        )