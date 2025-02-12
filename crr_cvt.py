import clipboard
import time
import requests
from tkinter import *
from tkinter import ttk
import re
import pystray
from PIL import Image
import io
from PIL import ImageDraw
import threading
import sys
from datetime import datetime

class CurrencyConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("환율 변환기")
        
        # 변수 초기화
        self.setup_variables()
        
        # GUI 생성
        self.create_gui()
        
        # 창 설정 (GUI 생성 후에 위치 지정)
        self.setup_window()
        
        # 나머지 설정
        self.create_tray_icon()
        self.setup_bindings()
        self.start_monitoring()
        
        # 로그 파일 경로 설정
        self.log_file = "currency_converter.log"
        
        # 모니터링 스레드 설정
        self.monitor_thread = None
        self.is_monitoring = True
        
        # 마우스 드래그로 창 이동 가능하게 설정
        self.root.bind('<Button-1>', self.start_move)
        self.root.bind('<B1-Motion>', self.do_move)
    
    def setup_window(self):
        # 창 스타일 설정
        self.root.configure(bg='black')  # 외부 테두리 색상을 검정으로
        self.root.overrideredirect(True)  # 창 테두리 제거
        self.root.wm_attributes("-topmost", True)  # 항상 위에 표시
        self.root.wm_attributes('-alpha', 0.98)  # 투명도
        
        # 초기 창 크기 설정
        window_width = 200
        window_height = 70
        
        # 화면 중앙에 표시
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def setup_variables(self):
        self.last_clipboard = ""
        self.auto_hide = BooleanVar(value=False)
        self._hide_job = None
        self.is_monitoring = True
        self.exchange_rates = self.get_default_rates()
    
    def get_default_rates(self):
        return {
            'USD': 0.00075,  # 1원 = 0.00075 USD (1 USD ≈ 1,330원)
            'JPY': 0.113,    # 1원 = 0.113 JPY (1 JPY ≈ 8.85원)
            'EUR': 0.00069,  # 1원 = 0.00069 EUR (1 EUR ≈ 1,450원)
            'CNY': 0.0054    # 1원 = 0.0054 CNY (1 CNY ≈ 185원)
        }
    
    def create_tray_icon(self):
        icon_image = self.create_icon_image()
        menu = (
            pystray.MenuItem("보이기", self.show_window),
            pystray.MenuItem("숨기기", self.hide_window),
            pystray.MenuItem("종료", self.quit_app)
        )
        self.icon = pystray.Icon("crr_cvt", icon_image, "환율 변환기", menu)
        self.icon.on_activate = self.show_window
        self.icon.run_detached()
    
    def create_icon_image(self):
        icon_size = 16
        image = Image.new('RGB', (icon_size, icon_size), color='white')
        draw = ImageDraw.Draw(image)
        draw.text((4, 1), '$', fill='black')
        return image
    
    def get_cursor_pos(self):
        """현재 마우스 커서 위치 가져오기"""
        return (self.root.winfo_pointerx(), self.root.winfo_pointery())
    
    def get_center_position(self, width, height):
        """창의 중앙 위치 계산"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        return x, y
    
    def show_window(self, icon=None, item=None):
        # 결과 텍스트 크기에 따라 창 크기 조정
        self.root.update_idletasks()
        result_width = self.result_label.winfo_reqwidth() + 20
        
        # 최소/최대 창 크기 설정
        window_width = max(200, min(300, result_width))
        window_height = 70
        
        # 트레이 아이콘에서 호출된 경우 화면 중앙에 표시
        if icon is not None:
            x, y = self.get_center_position(window_width, window_height)
        else:
            # 일반적인 경우 마우스 커서 위에 표시
            x, y = self.get_cursor_pos()
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = min(max(x - window_width//2, 0), screen_width - window_width)
            y = min(max(y - window_height - 20, 0), screen_height - window_height)
        
        # 창 크기와 위치 설정
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 이전 예약된 자동 숨김 취소
        if hasattr(self, '_hide_job') and self._hide_job:
            try:
                self.root.after_cancel(self._hide_job)
            except ValueError:
                pass  # 유효하지 않은 ID인 경우 무시
            self._hide_job = None
        
        # 창 표시
        self.root.deiconify()
        
        # 자동 숨김이 활성화된 경우에만 5초 후 숨기기 예약
        if self.auto_hide.get():
            self._hide_job = self.root.after(5000, self.hide_window)
    
    def hide_window(self, icon=None, item=None):
        # 이전 예약된 자동 숨김 취소
        if hasattr(self, '_hide_job') and self._hide_job:
            try:
                self.root.after_cancel(self._hide_job)
            except ValueError:
                pass  # 유효하지 않은 ID인 경우 무시
            self._hide_job = None
        
        # 창 숨기기
        self.root.withdraw()
    
    def quit_app(self, icon=None, item=None):
        # 모니터링 중지
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        self.icon.stop()
        self.root.quit()
    
    def create_gui(self):
        # 메인 프레임 (1픽셀 검정 테두리)
        main_frame = Frame(self.root, bg='black')
        main_frame.pack(fill=BOTH, expand=True, padx=2, pady=2)
        
        # 내부 프레임 (흰색 배경)
        inner_frame = Frame(main_frame, bg='white')
        inner_frame.pack(fill=BOTH, expand=True)
        
        # 결과 표시 영역
        result_frame = Frame(inner_frame, bg='white', height=30)  # 높이 축소
        result_frame.pack(fill=X)
        result_frame.pack_propagate(0)
        
        # 환율 결과
        self.result_label = Label(
            result_frame, 
            text="변환 결과가 여기에 표시됩니다",
            font=('맑은 고딕', 16, 'bold'),  # 폰트 크기 축소
            anchor=CENTER,
            bg='white',
            fg='#333333'
        )
        self.result_label.pack(fill=BOTH)
        
        # 컨트롤 프레임 (하단)
        control_frame = Frame(inner_frame, bg='white', height=25)
        control_frame.pack(fill=X, side=BOTTOM, pady=(0, 5))  # 하단 여백 5픽셀 추가
        control_frame.pack_propagate(0)
        
        # 왼쪽 컨트롤
        left_control = Frame(control_frame, bg='white')
        left_control.pack(side=LEFT, padx=5)  # 외부 여백 5픽셀
        
        # 자동 숨김 체크박스
        self.auto_hide_cb = Checkbutton(
            left_control, 
            text="자동 숨김", 
            variable=self.auto_hide,
            font=('맑은 고딕', 11),
            bg='white',
            activebackground='white',
            fg='black',
            selectcolor='white',
            activeforeground='black',
            highlightthickness=0,
            padx=2,
            pady=2
        )
        self.auto_hide_cb.pack(side=LEFT)
        
        # 오른쪽 컨트롤
        right_control = Frame(control_frame, bg='white')
        right_control.pack(side=RIGHT, padx=5)
        
        # 버튼 공통 스타일
        button_style = {
            'font': ('맑은 고딕', 11),
            'width': 4,
            'height': 1,
            'relief': 'solid',
            'borderwidth': 1,
            'bg': 'white',
            'activebackground': '#f0f0f0',
            'padx': 2,
            'pady': 2
        }
        
        # 종료 버튼 (먼저 배치)
        self.quit_button = Button(
            right_control,
            text="종료",
            command=self.quit_app,
            fg='#ff3b30',
            **button_style
        )
        self.quit_button.pack(side=RIGHT, padx=1)
        
        # 숨김 버튼 (나중에 배치)
        self.hide_button = Button(
            right_control,
            text="숨김",
            command=self.hide_window,
            fg='black',
            **button_style
        )
        self.hide_button.pack(side=RIGHT)
    
    def setup_bindings(self):
        self.root.bind('<<CheckClipboard>>', lambda e: self.check_clipboard())
        self.root.bind('<Button-1>', self.start_move)
        self.root.bind('<B1-Motion>', self.do_move)
    
    def start_monitoring(self):
        self.monitor_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        self.monitor_thread.start()
    
    def update_exchange_rates(self):
        try:
            # 환율 API 호출 (ExchangeRate-API 대신 frankfurter API 사용)
            url = "https://api.frankfurter.app/latest?from=KRW"
            response = requests.get(url)
            response.raise_for_status()  # HTTP 에러 체크
            data = response.json()
            
            # 원화 기준으로 환율 저장
            self.exchange_rates = {
                'USD': data['rates']['USD'],
                'JPY': data['rates']['JPY'],
                'EUR': data['rates']['EUR'],
                'CNY': data['rates']['CNY']
            }
            
        except Exception as e:
            print(f"환율 정보 업데이트 실패: {e}")
            # 기본 환율 설정 (2024년 3월 19일 기준 대략적인 값)
            self.exchange_rates = {
                'USD': 0.00075,  # 1원 = 0.00075 USD (1 USD ≈ 1,330원)
                'JPY': 0.113,    # 1원 = 0.113 JPY (1 JPY ≈ 8.85원)
                'EUR': 0.00069,  # 1원 = 0.00069 EUR (1 EUR ≈ 1,450원)
                'CNY': 0.0054    # 1원 = 0.0054 CNY (1 CNY ≈ 185원)
            }
    
    def show_popup(self):
        # show_window 메서드 호출
        self.show_window()
    
    def log_conversion(self, original, converted):
        """환율 변환 로그를 콘솔에 출력"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {original} -> {converted}"
            print(log_entry)  # 콘솔에 출력
        except Exception as e:
            print(f"로그 출력 실패: {e}")
    
    def check_clipboard(self):
        try:
            clipboard_content = clipboard.paste()
            
            # 클립보드 내용이 변경되었고 숫자를 포함하는 경우에만 처리
            if clipboard_content != self.last_clipboard:
                self.last_clipboard = clipboard_content
                
                # 통화 기호와 공백 제거
                clipboard_content = (clipboard_content
                    .replace('$', 'USD')
                    .replace('¥', 'JPY')
                    .replace('€', 'EUR')
                    .replace('￥', 'JPY')
                    .replace('元', 'CNY')
                    .replace('￦', '')
                    .replace('₩', '')
                    .strip())
                
                # 숫자와 통화 코드 추출
                match = re.search(r'([\d,.]+)\s*(USD|JPY|EUR|CNY)?', clipboard_content, re.IGNORECASE)
                if match:
                    amount_str, currency = match.groups()
                    # 쉼표 제거 후 숫자 변환
                    amount = float(amount_str.replace(',', ''))
                    
                    # 통화가 지정되지 않은 경우 USD로 가정
                    currency = (currency or 'USD').upper()
                    
                    if currency in self.exchange_rates:
                        # 특정 통화만 변환
                        rate = self.exchange_rates[currency]
                        converted = amount / rate
                        original = f"{amount:,.2f} {currency}"
                        converted_str = f"{converted:,.0f}원"
                        result = f"{original} = {converted_str}"
                        
                        # 결과 표시
                        self.result_label.config(text=result)
                        
                        # 로그 기록
                        self.log_conversion(original, converted_str)
                        
                        # 결과가 업데이트될 때마다 팝업 표시
                        self.show_popup()
        except Exception as e:
            print(f"클립보드 처리 오류: {e}")  # 오류 메시지 변경
            # 오류도 로그에 기록
            self.log_conversion("오류", str(e))
    
    def monitor_clipboard(self):
        """클립보드 모니터링 스레드 함수"""
        while self.is_monitoring:
            try:
                # GUI 업데이트를 메인 스레드에 안전하게 요청
                if self.root and self.root.winfo_exists():
                    self.root.event_generate('<<CheckClipboard>>')
                time.sleep(0.5)  # 체크 간격을 0.5초로 줄임
            except Exception as e:
                print(f"모니터링 오류: {e}")
    
    def start_move(self, event):
        self.x = event.x
        self.y = event.y
    
    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

def main():
    root = Tk()
    app = CurrencyConverter(root)
    root.mainloop()

if __name__ == "__main__":
    main()