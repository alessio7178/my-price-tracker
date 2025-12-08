import flet as ft
import requests
import urllib.parse
import json
import threading
import time
import os
from datetime import datetime

# ==========================================
# ⚙️ 네이버 API 키
# ==========================================
NAVER_CLIENT_ID = "bx_DGnA61axCz5zZSOYk"
NAVER_CLIENT_SECRET = "3f9BnBNGzb"

# 데이터 파일
WISHLIST_FILE = "wishlist.json"

# 🎨 디자인 테마
BG_COLOR = "#191919"       
CARD_COLOR = "#2C2C2C"     
TEXT_COLOR = "#FFFFFF"     
SUB_TEXT_COLOR = "#B0B8C1" 
ACCENT_COLOR = "#3182F6"   
ERROR_COLOR = "#FF3B30"
INPUT_BG = "#333333"       

# 알림 라이브러리
try:
    from plyer import notification
except ImportError:
    notification = None

def main(page: ft.Page):
    page.title = "My Price Tracker"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG_COLOR
    page.padding = 0
    page.window_width = 390
    page.window_height = 844
    page.keep_screen_on = True 

    # --- 데이터 로드 ---
    my_wishlist = []
    if os.path.exists(WISHLIST_FILE):
        try:
            with open(WISHLIST_FILE, "r", encoding="utf-8") as f:
                my_wishlist = json.load(f)
        except:
            my_wishlist = []

    def save_data():
        try:
            with open(WISHLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(my_wishlist, f, ensure_ascii=False, indent=4)
        except:
            pass

    # --- 알림 함수 ---
    def send_app_notification(title, message):
        page.open(ft.SnackBar(
            content=ft.Text(f"{title}\n{message}", color="white"),
            bgcolor=ACCENT_COLOR,
            action="확인",
            duration=3000
        ))
        
        if notification:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="최저가 사냥꾼",
                    timeout=5,
                    ticker="알림"
                )
            except: pass

    def show_error_dialog(error_msg):
        dlg = ft.AlertDialog(
            title=ft.Text("⚠️ 알림", color=ERROR_COLOR),
            content=ft.Text(f"{error_msg}", color=TEXT_COLOR),
            actions=[ft.TextButton("확인", on_click=lambda e: page.close(dlg))],
            bgcolor=CARD_COLOR
        )
        page.open(dlg)

    # =================================================================
    # 🤖 1시간 자동 감시 루프
    # =================================================================
    def auto_monitor_loop():
        # 시작 알림 (권한 테스트 겸)
        time.sleep(3)
        send_app_notification("👁️ 감시 시작", "백그라운드 감시가 활성화되었습니다.")
        
        while True:
            for _ in range(360):
                time.sleep(10)

            if not my_wishlist: continue
            
            headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
            updated_count = 0
            
            for i, item in enumerate(my_wishlist):
                try:
                    encText = urllib.parse.quote(item['title'])
                    url = f"https://openapi.naver.com/v1/search/shop.json?query={encText}&display=1&sort=sim"
                    
                    res = requests.get(url, headers=headers)
                    items = res.json().get('items', [])
                    
                    if items:
                        current_price = int(items[0]['lprice'])
                        target_price = item['target_price']
                        
                        if my_wishlist[i]['price'] != current_price:
                            my_wishlist[i]['price'] = current_price
                            updated_count += 1
                        
                        if current_price <= target_price:
                            send_app_notification(
                                "🔔 목표가 달성!", 
                                f"[{item['mall']}] {item['title'][:10]}...\n현재가: {current_price:,}원"
                            )
                except: pass
            
            if updated_count > 0:
                save_data()

    threading.Thread(target=auto_monitor_loop, daemon=True).start()

    # =================================================================
    # 🧩 UI 컴포넌트
    # =================================================================
    class KeywordManager(ft.Column):
        def __init__(self, label_text, hint_text, chip_color=TEXT_COLOR):
            super().__init__()
            self.keywords = [] 
            self.chip_color = chip_color
            
            self.chip_row = ft.Row(wrap=True, spacing=5)
            self.input_field = ft.TextField(
                label=label_text, hint_text=hint_text, border_color="transparent", bgcolor=INPUT_BG, color=TEXT_COLOR,
                text_size=14, border_radius=10, content_padding=15,
                hint_style=ft.TextStyle(color=SUB_TEXT_COLOR, font_family="NotoSansKR"),
                label_style=ft.TextStyle(color=SUB_TEXT_COLOR, font_family="NotoSansKR"),
                on_submit=self.add_keyword
            )
            self.controls = [self.input_field, self.chip_row]
            self.spacing = 10

        def add_keyword(self, e):
            text = self.input_field.value.strip()
            if text:
                for word in text.replace(",", " ").split():
                    if word and word not in self.keywords:
                        self.keywords.append(word)
                        self.chip_row.controls.append(
                            ft.Chip(label=ft.Text(word, color=self.chip_color, font_family="NotoSansKR"), bgcolor=CARD_COLOR,
                                    on_delete=self.delete_keyword, data=word, delete_icon_color=SUB_TEXT_COLOR))
                self.input_field.value = ""
                self.update()

        def delete_keyword(self, e):
            word = e.control.data
            if word in self.keywords:
                self.keywords.remove(word)
                self.chip_row.controls.remove(e.control)
                self.update()

    km_must = KeywordManager("필수 포함 키워드", "예: 정품", ACCENT_COLOR)
    km_exclude = KeywordManager("제외 키워드", "예: 호환", ERROR_COLOR)

    # --- 메인 UI 요소 ---
    header = ft.Container(
        content=ft.Row([
            ft.Text("My Price Tracker", size=24, weight="bold", color=TEXT_COLOR),
            ft.Icon(name="notifications_active", color=ACCENT_COLOR)
        ], alignment="spaceBetween"),
        padding=ft.padding.symmetric(horizontal=20, vertical=15),
        bgcolor=BG_COLOR
    )

    txt_main_keyword = ft.TextField(label="메인 검색어", hint_text="예: 비쎌 청소기", border_color="transparent", bgcolor=INPUT_BG, border_radius=15, prefix_icon="search", color=TEXT_COLOR, text_size=16, hint_style=ft.TextStyle(color=SUB_TEXT_COLOR, font_family="NotoSansKR"), label_style=ft.TextStyle(color=SUB_TEXT_COLOR, font_family="NotoSansKR"))
    txt_min_price = ft.TextField(label="최소 가격", value="0", width=120, text_align="right", bgcolor=INPUT_BG, border_color="transparent", border_radius=10, color=TEXT_COLOR, text_size=14)
    txt_max_price = ft.TextField(label="목표 가격", value="45000", width=120, text_align="right", bgcolor=INPUT_BG, border_color="transparent", border_radius=10, color=TEXT_COLOR, text_size=14)

    rg_sort = ft.RadioGroup(content=ft.Row([
        ft.Radio(value="sim", label="랭킹순(추천)", fill_color=ACCENT_COLOR),
        ft.Radio(value="asc", label="최저가순", fill_color=ACCENT_COLOR)
    ]), value="sim")

    mall_mapping = {"쿠팡": ["쿠팡"], "G마켓": ["G마켓", "지마켓"], "옥션": ["옥션"], "11번가": ["11번가"], "오늘의집": ["오늘의집"], "Kurly": ["컬리", "Kurly", "마켓컬리"], "신세계": ["SSG", "신세계", "이마트"], "롯데온": ["롯데"]}
    selected_malls_ui = []
    def toggle_mall(e): e.control.selected = not e.control.selected; e.control.update()
    row_malls = ft.Row(scroll="hidden")
    for m in mall_mapping.keys():
        chip = ft.Chip(label=ft.Text(m, color=TEXT_COLOR, font_family="NotoSansKR"), on_click=toggle_mall, bgcolor=CARD_COLOR, selected_color=ACCENT_COLOR, show_checkmark=False)
        row_malls.controls.append(chip)
        selected_malls_ui.append(chip)

    btn_search = ft.ElevatedButton("검색 시작", on_click=lambda e: run_search(e), bgcolor=ACCENT_COLOR, color="white", width=400, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)))

    search_inputs_container = ft.Container(
        content=ft.Column([
            txt_main_keyword, km_must, km_exclude,
            ft.Row([txt_min_price, ft.Text("~", color=SUB_TEXT_COLOR), txt_max_price], alignment="spaceBetween"),
            rg_sort, ft.Text("판매처 (옆으로 스크롤)", size=12, color=SUB_TEXT_COLOR, font_family="NotoSansKR"), row_malls,
            ft.Container(height=10),
            btn_search
        ], spacing=15),
        padding=20, visible=True
    )
    
    toggle_icon = ft.Icon(name="expand_less", color=ACCENT_COLOR)
    def toggle_search_box(e):
        search_inputs_container.visible = not search_inputs_container.visible
        toggle_icon.name = "expand_more" if not search_inputs_container.visible else "expand_less"
        page.update()

    search_header_row = ft.Container(content=ft.Row([ft.Text("🔍 검색 조건 설정", color=ACCENT_COLOR, weight="bold", size=16), toggle_icon], alignment="spaceBetween"), padding=10, bgcolor=BG_COLOR, on_click=toggle_search_box)
    lv_results = ft.ListView(expand=True, spacing=15, padding=20)
    loading_overlay = ft.Container(content=ft.Column([ft.ProgressRing(width=50, height=50, color=ACCENT_COLOR, stroke_width=4), ft.Text("최저가를 찾고 있어요...", size=18, weight="bold", color=TEXT_COLOR, font_family="NotoSansKR"), ft.Text("잠시만 기다려주세요", size=14, color=SUB_TEXT_COLOR, font_family="NotoSansKR")], alignment="center", horizontal_alignment="center", spacing=20), alignment=ft.alignment.center, bgcolor="#E6191919", visible=False, expand=True)

    # --- 검색 로직 ---
    def run_search(e):
        search_inputs_container.visible = False
        toggle_icon.name = "expand_more"
        loading_overlay.visible = True
        page.update()
        
        main_kwd = txt_main_keyword.value
        if not main_kwd:
            loading_overlay.visible = False; search_inputs_container.visible = True; show_message("검색어를 입력해주세요!", bgcolor=ERROR_COLOR); page.update(); return

        def search_thread():
            try:
                min_p = int(txt_min_price.value) if txt_min_price.value else 0
                max_p = int(txt_max_price.value) if txt_max_price.value else 0
                query = main_kwd
                if km_must.keywords:
                    for w in km_must.keywords: query += f" {w}"
                exclude_list = km_exclude.keywords
                target_keywords = []
                for chip in selected_malls_ui:
                    if chip.selected: target_keywords.extend(mall_mapping[chip.label.value])

                collected = []
                headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
                for page_num in range(10): 
                    start = (page_num * 100) + 1
                    encText = urllib.parse.quote(query)
                    url = f"https://openapi.naver.com/v1/search/shop.json?query={encText}&display=100&start={start}&sort={rg_sort.value}&exclude=used:rental:cbshop"
                    try:
                        res = requests.get(url, headers=headers, timeout=5)
                        items = res.json().get('items', [])
                        if not items: break
                    except: break
                    for item in items:
                        title = item['title'].replace("<b>", "").replace("</b>", "")
                        mall = item['mallName']
                        price = int(item['lprice'])
                        link = item['link']
                        if any(bad in title for bad in exclude_list): continue
                        if not (min_p <= price): continue
                        if max_p > 0 and price > max_p: continue
                        if target_keywords:
                            is_wanted = False
                            for kw in target_keywords:
                                if kw.lower() in mall.lower(): is_wanted = True; break
                            if not is_wanted: continue
                        collected.append({"title": title, "mall": mall, "price": price, "link": link})
                    if len(collected) >= 30: break
                collected.sort(key=lambda x: x['price'])
                lv_results.controls.clear()
                if not collected:
                    lv_results.controls.append(ft.Container(content=ft.Text("조건에 맞는 상품이 없습니다.", color=SUB_TEXT_COLOR, font_family="NotoSansKR"), alignment=ft.alignment.center, padding=50))
                else:
                    send_app_notification("검색 완료", f"{len(collected)}개의 최저가를 찾았습니다!")
                    for idx, item in enumerate(collected[:10]):
                        card = ft.Container(content=ft.Column([ft.Row([ft.Container(content=ft.Text(str(idx+1), weight="bold", color="white", font_family="NotoSansKR-Bold"), bgcolor=ACCENT_COLOR if idx < 3 else "#444", border_radius=5, width=24, height=24, alignment=ft.alignment.center), ft.Text(f"[{item['mall']}]", size=12, color=SUB_TEXT_COLOR, font_family="NotoSansKR"), ft.Container(expand=True), ft.IconButton(icon="favorite_border", icon_color="white", on_click=lambda e, i=item: open_zzim_dialog(i))], alignment="spaceBetween"), ft.Text(item['title'], max_lines=2, overflow="ellipsis", weight="bold", size=15, font_family="NotoSansKR"), ft.Container(height=5), ft.Row([ft.Text(f"{item['price']:,}원", size=18, weight="bold", color=ACCENT_COLOR, font_family="NotoSansKR-Bold"), ft.ElevatedButton("구매", url=item['link'], style=ft.ButtonStyle(bgcolor="#333333", color="white", shape=ft.RoundedRectangleBorder(radius=8)), height=35)], alignment="spaceBetween")]), bgcolor=CARD_COLOR, padding=15, border_radius=15)
                        lv_results.controls.append(card)
            except Exception as err: show_error_dialog(str(err))
            finally: loading_overlay.visible = False; page.update()
        threading.Thread(target=search_thread).start()

    # --- 찜하기 ---
    def open_zzim_dialog(item):
        if len(my_wishlist) >= 50: send_app_notification("알림", "찜 목록은 최대 50개까지만 가능합니다."); return
        target_price_field = ft.TextField(label="목표 가격", value=str(item['price']), text_align="right", border_color=ACCENT_COLOR)
        def save_zzim(e):
            new_item = item.copy(); new_item['target_price'] = int(target_price_field.value); my_wishlist.append(new_item); save_data(); page.close(dlg_zzim); send_app_notification("찜 등록 완료", f"'{item['title'][:10]}...' 감시 시작"); refresh_wishlist_tab()
        dlg_zzim = ft.AlertDialog(modal=True, bgcolor=CARD_COLOR, title=ft.Text("알림 설정", color=TEXT_COLOR, font_family="NotoSansKR-Bold"), content=ft.Column([ft.Text(f"상품: {item['title']}", size=12, color=SUB_TEXT_COLOR, font_family="NotoSansKR"), ft.Divider(color="#444"), target_price_field, ft.Text("이 가격 이하가 되면 알림을 보냅니다.", size=12, color=SUB_TEXT_COLOR, font_family="NotoSansKR")], height=150, width=300), actions=[ft.TextButton("취소", on_click=lambda e: page.close(dlg_zzim), style=ft.ButtonStyle(color=SUB_TEXT_COLOR)), ft.ElevatedButton("저장", on_click=save_zzim, bgcolor=ACCENT_COLOR, color="white")])
        page.open(dlg_zzim)

    # --- 찜 목록 탭 ---
    lv_wishlist_tab = ft.ListView(expand=True, spacing=10, padding=20)
    def refresh_wishlist_tab():
        lv_wishlist_tab.controls.clear()
        lv_wishlist_tab.controls.append(ft.Container(content=ft.Row([ft.Text(f"내 찜 목록 ({len(my_wishlist)}/50)", color=ACCENT_COLOR, weight="bold", font_family="NotoSansKR-Bold")], alignment="spaceBetween"), padding=10, border=ft.border.only(bottom=ft.border.BorderSide(1, "#333"))))
        if not my_wishlist: lv_wishlist_tab.controls.append(ft.Container(content=ft.Text("찜한 상품이 없어요.", color=SUB_TEXT_COLOR, font_family="NotoSansKR"), alignment=ft.alignment.center, padding=50))
        for idx, item in enumerate(my_wishlist):
            lv_wishlist_tab.controls.append(ft.Container(content=ft.Row([ft.Column([ft.Text(item['title'], width=200, max_lines=1, overflow="ellipsis", weight="bold", font_family="NotoSansKR"), ft.Text(f"현재: {item['price']:,}원", color=SUB_TEXT_COLOR, size=12, font_family="NotoSansKR"), ft.Text(f"목표: {item['target_price']:,}원", color=ACCENT_COLOR, size=12, weight="bold", font_family="NotoSansKR-Bold")]), ft.IconButton(icon="delete", icon_color="grey", on_click=lambda e, i=idx: delete_wishlist(i))], alignment="spaceBetween"), bgcolor=CARD_COLOR, padding=15, border_radius=15))
        page.update()
    def delete_wishlist(index): del my_wishlist[index]; save_data(); refresh_wishlist_tab()

    # --- [추가] 권한 재요청 함수 ---
    def request_permissions(e):
        send_app_notification("알림 테스트", "이 알림이 보이면 성공입니다!")
    
    # --- 설정 탭 ---
    def reset_all(e): my_wishlist.clear(); save_data(); refresh_wishlist_tab(); send_app_notification("초기화 완료", "모든 찜 목록이 삭제되었습니다.")
    settings_view = ft.Container(content=ft.Column([
        ft.Text("앱 설정", size=18, weight="bold", color=TEXT_COLOR, font_family="NotoSansKR-Bold"), ft.Divider(color="#444"),
        ft.ListTile(leading=ft.Icon(name="notifications", color=ACCENT_COLOR), title=ft.Text("알림 권한 재요청", color=TEXT_COLOR), subtitle=ft.Text("알림이 안 온다면 눌러보세요.", color=SUB_TEXT_COLOR), on_click=request_permissions),
        ft.ListTile(leading=ft.Icon(name="delete_forever", color=ERROR_COLOR), title=ft.Text("데이터 초기화", color=TEXT_COLOR), subtitle=ft.Text("찜 목록을 모두 삭제합니다.", color=SUB_TEXT_COLOR), on_click=reset_all),
        ft.Container(height=20), ft.Text("Version 4.1 (New ID Build)", size=12, color="grey")
    ], spacing=10), padding=20)

    # --- 메인 탭바 ---
    tabs = ft.Tabs(selected_index=0, divider_color="transparent", indicator_color=ACCENT_COLOR, label_color=ACCENT_COLOR, unselected_label_color="grey", tabs=[ft.Tab(icon="search", text="검색"), ft.Tab(icon="favorite", text="찜 목록"), ft.Tab(icon="settings", text="설정")], on_change=lambda e: refresh_wishlist_tab())
    content_area = ft.Container(expand=True)
    def on_tab_click(e):
        idx = tabs.selected_index
        content_area.content = [ft.Container(content=ft.Column([search_header_row, search_inputs_container, lv_results])), lv_wishlist_tab, settings_view][idx]; page.update()
    tabs.on_change = on_tab_click
    page.add(ft.Stack([ft.Column([header, ft.Container(content=tabs, bgcolor=BG_COLOR), ft.Divider(height=1, color="#333"), content_area], expand=True), loading_overlay], expand=True))
    on_tab_click(None); refresh_wishlist_tab()

ft.app(target=main)
