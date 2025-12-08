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
SETTINGS_FILE = "settings.json"

# 🎨 디자인 테마
BG_COLOR = "#191919"
CARD_COLOR = "#2C2C2C"
TEXT_COLOR = "#FFFFFF"
SUB_TEXT_COLOR = "#B0B8C1"
ACCENT_COLOR = "#3182F6"
ERROR_COLOR = "#FF3B30"
INPUT_BG = "#333333"


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
    app_settings = {"plan": "FREE", "tele_token": "", "tele_id": ""}

    if os.path.exists(WISHLIST_FILE):
        try:
            with open(WISHLIST_FILE, "r", encoding="utf-8") as f:
                my_wishlist = json.load(f)
        except:
            my_wishlist = []

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                app_settings.update(json.load(f))
        except:
            pass

    def save_data():
        try:
            with open(WISHLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(my_wishlist, f, ensure_ascii=False, indent=4)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(app_settings, f, ensure_ascii=False, indent=4)
        except:
            pass

    # --- 텔레그램 발송 ---
    def send_telegram(text):
        token = app_settings.get("tele_token", "")
        chat_id = app_settings.get("tele_id", "")
        if not token or not chat_id: return
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            params = {"chat_id": chat_id, "text": text}
            requests.get(url, params=params)
        except:
            pass

    # --- UI 알림 ---
    def show_message(text, color="white", bgcolor="#333333"):
        snack = ft.SnackBar(
            content=ft.Text(text, color=color, font_family="NotoSansKR"),
            bgcolor=bgcolor,
            action="확인",
            action_color=ACCENT_COLOR
        )
        page.open(snack)

    def show_error_dialog(error_msg):
        dlg = ft.AlertDialog(
            title=ft.Text("⚠️ 알림", color=ERROR_COLOR),
            content=ft.Text(f"{error_msg}", color=TEXT_COLOR),
            actions=[ft.TextButton("확인", on_click=lambda e: page.close(dlg))],
            bgcolor=CARD_COLOR
        )
        page.open(dlg)
        send_telegram(f"🚨 [오류]\n{error_msg}")

    # =================================================================
    # 🧩 키워드 칩 UI
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
                            ft.Chip(label=ft.Text(word, color=self.chip_color, font_family="NotoSansKR"),
                                    bgcolor=CARD_COLOR,
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

    # =================================================================
    # 🏠 메인 UI
    # =================================================================
    header = ft.Container(
        content=ft.Row([
            ft.Text("My Price Tracker", size=24, weight="bold", color=TEXT_COLOR),
            ft.Icon(name="notifications_active", color=ACCENT_COLOR)
        ], alignment="spaceBetween"),
        padding=ft.padding.symmetric(horizontal=20, vertical=15),
        bgcolor=BG_COLOR
    )

    # --- 검색 입력창 UI 요소 ---
    txt_main_keyword = ft.TextField(
        label="메인 검색어", hint_text="예: 비쎌 청소기", border_color="transparent", bgcolor=INPUT_BG, border_radius=15,
        prefix_icon="search", color=TEXT_COLOR, text_size=16,
        hint_style=ft.TextStyle(color=SUB_TEXT_COLOR, font_family="NotoSansKR"),
        label_style=ft.TextStyle(color=SUB_TEXT_COLOR, font_family="NotoSansKR")
    )

    txt_min_price = ft.TextField(label="최소 가격", value="0", width=120, text_align="right", bgcolor=INPUT_BG,
                                 border_color="transparent", border_radius=10, color=TEXT_COLOR, text_size=14)
    txt_max_price = ft.TextField(label="목표 가격", value="45000", width=120, text_align="right", bgcolor=INPUT_BG,
                                 border_color="transparent", border_radius=10, color=TEXT_COLOR, text_size=14)

    rg_sort = ft.RadioGroup(content=ft.Row([
        ft.Radio(value="sim", label="랭킹순(추천)", fill_color=ACCENT_COLOR),
        ft.Radio(value="asc", label="최저가순", fill_color=ACCENT_COLOR)
    ]), value="sim")

    mall_mapping = {
        "쿠팡": ["쿠팡"], "G마켓": ["G마켓", "지마켓"], "옥션": ["옥션"],
        "11번가": ["11번가"], "오늘의집": ["오늘의집"],
        "Kurly": ["컬리", "Kurly", "마켓컬리"], "신세계": ["SSG", "신세계", "이마트"], "롯데온": ["롯데"]
    }

    selected_malls_ui = []

    def toggle_mall(e):
        e.control.selected = not e.control.selected
        e.control.update()

    row_malls = ft.Row(scroll="hidden")
    for m in mall_mapping.keys():
        chip = ft.Chip(
            label=ft.Text(m, color=TEXT_COLOR, font_family="NotoSansKR"),
            on_click=toggle_mall,
            bgcolor=CARD_COLOR,
            selected_color=ACCENT_COLOR,
            show_checkmark=False
        )
        row_malls.controls.append(chip)
        selected_malls_ui.append(chip)

    lv_results = ft.ListView(expand=True, spacing=15, padding=20)

    loading_overlay = ft.Container(
        content=ft.Column([
            ft.ProgressRing(width=50, height=50, color=ACCENT_COLOR, stroke_width=4),
            ft.Text("최저가를 찾고 있어요...", size=18, weight="bold", color=TEXT_COLOR, font_family="NotoSansKR"),
            ft.Text("잠시만 기다려주세요", size=14, color=SUB_TEXT_COLOR, font_family="NotoSansKR")
        ], alignment="center", horizontal_alignment="center", spacing=20),
        alignment=ft.alignment.center, bgcolor="#E6191919", visible=False, expand=True,
    )

    # --- [수정된 부분] 수동 아코디언 (접기/펴기) ---
    search_inputs_col = ft.Column([
        txt_main_keyword,
        km_must,
        km_exclude,
        ft.Row([txt_min_price, ft.Text("~", color=SUB_TEXT_COLOR), txt_max_price], alignment="spaceBetween"),
        rg_sort,
        ft.Text("판매처 (옆으로 스크롤)", size=12, color=SUB_TEXT_COLOR, font_family="NotoSansKR"),
        row_malls,
        ft.Container(height=10)
    ], spacing=15, visible=True)

    def toggle_search_panel(e):
        # 현재 상태의 반대로 설정
        search_inputs_col.visible = not search_inputs_col.visible
        # 아이콘 변경
        icon_name = "expand_more" if not search_inputs_col.visible else "expand_less"
        btn_toggle.icon = icon_name
        page.update()

    btn_toggle = ft.IconButton(icon="expand_less", icon_color=SUB_TEXT_COLOR, on_click=toggle_search_panel)

    search_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("🔍 검색 조건 설정", color=ACCENT_COLOR, weight="bold", size=16),
                btn_toggle
            ], alignment="spaceBetween"),
            search_inputs_col,
            # 검색 버튼은 항상 보이게 밖으로 뺌? 아니면 안에? -> 안에 넣어서 같이 접히게
            ft.ElevatedButton("검색 시작", on_click=lambda e: run_search(e), bgcolor=ACCENT_COLOR, color="white", width=400,
                              height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)))
        ]),
        padding=20,
        bgcolor=BG_COLOR
    )

    # --- 검색 로직 ---
    def run_search(e):
        # 1. [핵심] 검색창 강제 접기
        search_inputs_col.visible = False
        btn_toggle.icon = "expand_more"  # 아이콘을 '펼치기' 모양으로 변경
        loading_overlay.visible = True
        page.update()

        main_kwd = txt_main_keyword.value
        if not main_kwd:
            loading_overlay.visible = False
            search_inputs_col.visible = True  # 다시 펼침
            btn_toggle.icon = "expand_less"
            show_message("검색어를 입력해주세요!", bgcolor=ERROR_COLOR)
            page.update()
            return

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
                    except:
                        break

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

                # UI 업데이트
                lv_results.controls.clear()
                if not collected:
                    lv_results.controls.append(ft.Container(
                        content=ft.Text("조건에 맞는 상품이 없습니다.", color=SUB_TEXT_COLOR, font_family="NotoSansKR"),
                        alignment=ft.alignment.center, padding=50))
                else:
                    show_message(f"{len(collected)}개의 최저가를 찾았습니다!", bgcolor=ACCENT_COLOR)
                    for idx, item in enumerate(collected[:10]):
                        card = ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(content=ft.Text(str(idx + 1), weight="bold", color="white",
                                                                 font_family="NotoSansKR-Bold"),
                                                 bgcolor=ACCENT_COLOR if idx < 3 else "#444", border_radius=5, width=24,
                                                 height=24, alignment=ft.alignment.center),
                                    ft.Text(f"[{item['mall']}]", size=12, color=SUB_TEXT_COLOR,
                                            font_family="NotoSansKR"),
                                    ft.Container(expand=True),
                                    ft.IconButton(icon="favorite_border", icon_color="white",
                                                  on_click=lambda e, i=item: open_zzim_dialog(i))
                                ], alignment="spaceBetween"),
                                ft.Text(item['title'], max_lines=2, overflow="ellipsis", weight="bold", size=15,
                                        font_family="NotoSansKR"),
                                ft.Container(height=5),
                                ft.Row([
                                    ft.Text(f"{item['price']:,}원", size=18, weight="bold", color=ACCENT_COLOR,
                                            font_family="NotoSansKR-Bold"),
                                    ft.ElevatedButton("구매", url=item['link'],
                                                      style=ft.ButtonStyle(bgcolor="#333333", color="white",
                                                                           shape=ft.RoundedRectangleBorder(radius=8)),
                                                      height=35)
                                ], alignment="spaceBetween")
                            ]),
                            bgcolor=CARD_COLOR, padding=15, border_radius=15,
                        )
                        lv_results.controls.append(card)

            except Exception as err:
                show_error_dialog(str(err))

            loading_overlay.visible = False
            page.update()

        threading.Thread(target=search_thread).start()

    # --- 찜하기 다이얼로그 ---
    def open_zzim_dialog(item):
        plan = app_settings.get('plan', 'FREE')
        limit = 1 if plan == "FREE" else (5 if plan == "BASIC" else 20)

        if len(my_wishlist) >= limit:
            show_message(f"🚨 {plan} 요금제는 {limit}개까지만 가능합니다!", bgcolor=ERROR_COLOR)
            return

        target_price_field = ft.TextField(label="목표 가격", value=str(item['price']), text_align="right",
                                          border_color=ACCENT_COLOR)

        def save_zzim(e):
            new_item = item.copy()
            new_item['target_price'] = int(target_price_field.value)
            my_wishlist.append(new_item)
            save_data()
            page.close(dlg_zzim)
            show_message("찜 목록에 저장 & 알림 등록 완료!", bgcolor=ACCENT_COLOR)
            send_telegram(f"🔔 [알림 등록]\n상품: {item['title']}\n목표가: {new_item['target_price']:,}원")
            refresh_wishlist_tab()

        dlg_zzim = ft.AlertDialog(
            modal=True, bgcolor=CARD_COLOR,
            title=ft.Text("알림 설정", color=TEXT_COLOR, font_family="NotoSansKR-Bold"),
            content=ft.Column([
                ft.Text(f"상품: {item['title']}", size=12, color=SUB_TEXT_COLOR, font_family="NotoSansKR"),
                ft.Divider(color="#444"),
                target_price_field,
                ft.Text("이 가격 이하가 되면 텔레그램으로 알림을 보냅니다.", size=12, color=SUB_TEXT_COLOR, font_family="NotoSansKR")
            ], height=150, width=300),
            actions=[ft.TextButton("취소", on_click=lambda e: page.close(dlg_zzim),
                                   style=ft.ButtonStyle(color=SUB_TEXT_COLOR)),
                     ft.ElevatedButton("저장", on_click=save_zzim, bgcolor=ACCENT_COLOR, color="white")]
        )
        page.open(dlg_zzim)

    # --- [설정 탭] ---
    def save_tele_settings(e):
        app_settings['tele_token'] = txt_tele_token.value
        app_settings['tele_id'] = txt_tele_id.value
        save_data()
        show_message("설정이 저장되었습니다.", bgcolor=ACCENT_COLOR)
        send_telegram("🔔 테스트 알림: 설정이 완료되었습니다!")

    txt_tele_token = ft.TextField(label="텔레그램 봇 토큰", password=True, can_reveal_password=True, text_size=12,
                                  color=TEXT_COLOR, border_color=CARD_COLOR, bgcolor=INPUT_BG)
    txt_tele_id = ft.TextField(label="내 채팅 ID", text_size=12, color=TEXT_COLOR, border_color=CARD_COLOR,
                               bgcolor=INPUT_BG)

    settings_view = ft.Container(
        content=ft.Column([
            ft.Text("알림 설정 (Telegram)", size=18, weight="bold", color=TEXT_COLOR),
            ft.Text("앱이 꺼져있어도 텔레그램으로 알림이 옵니다.", size=12, color=SUB_TEXT_COLOR),
            txt_tele_token,
            txt_tele_id,
            ft.ElevatedButton("설정 저장 및 테스트 발송", on_click=save_tele_settings, bgcolor=ACCENT_COLOR, color="white"),
            ft.Divider(color="#444"),
            ft.Text("내 요금제 설정", size=18, weight="bold", color=TEXT_COLOR),
        ], spacing=15),
        padding=20
    )

    txt_tele_token.value = app_settings.get("tele_token", "")
    txt_tele_id.value = app_settings.get("tele_id", "")

    def set_plan(plan_name):
        app_settings['plan'] = plan_name
        save_data()
        show_message(f"'{plan_name}' 요금제로 변경되었습니다!", bgcolor=ACCENT_COLOR)
        refresh_wishlist_tab()

    settings_view.content.controls.extend([
        ft.Container(content=ft.Row([ft.Column(
            [ft.Text("FREE (무료)", weight="bold", color=TEXT_COLOR), ft.Text("찜 1개", size=12, color=SUB_TEXT_COLOR)]),
                                     ft.ElevatedButton("선택", on_click=lambda e: set_plan("FREE"), bgcolor=CARD_COLOR,
                                                       color="white")], alignment="spaceBetween"), bgcolor=CARD_COLOR,
                     padding=15, border_radius=10),
        ft.Container(content=ft.Row([ft.Column([ft.Text("BASIC (1,900원)", weight="bold", color=TEXT_COLOR),
                                                ft.Text("찜 5개", size=12, color=SUB_TEXT_COLOR)]),
                                     ft.ElevatedButton("선택", on_click=lambda e: set_plan("BASIC"), bgcolor=CARD_COLOR,
                                                       color="white")], alignment="spaceBetween"), bgcolor=CARD_COLOR,
                     padding=15, border_radius=10),
        ft.Container(content=ft.Row([ft.Column([ft.Text("PRO (4,900원)", weight="bold", color=TEXT_COLOR),
                                                ft.Text("찜 20개", size=12, color=SUB_TEXT_COLOR)]),
                                     ft.ElevatedButton("선택", on_click=lambda e: set_plan("PRO"), bgcolor=CARD_COLOR,
                                                       color="white")], alignment="spaceBetween"), bgcolor=CARD_COLOR,
                     padding=15, border_radius=10)
    ])

    # --- [찜 목록 탭] ---
    lv_wishlist_tab = ft.ListView(expand=True, spacing=10, padding=20)

    def refresh_wishlist_tab():
        lv_wishlist_tab.controls.clear()
        plan_name = app_settings.get('plan', 'FREE')
        limit = 1 if plan_name == "FREE" else (5 if plan_name == "BASIC" else 20)

        lv_wishlist_tab.controls.append(ft.Container(content=ft.Row(
            [ft.Text(f"요금제: {plan_name}", color=ACCENT_COLOR, weight="bold"),
             ft.Text(f"({len(my_wishlist)}/{limit})", color=TEXT_COLOR)], alignment="spaceBetween"), padding=10))

        for idx, item in enumerate(my_wishlist):
            lv_wishlist_tab.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(item['title'], width=200, max_lines=1, overflow="ellipsis", weight="bold"),
                            ft.Text(f"현재: {item['price']:,}원", color=SUB_TEXT_COLOR, size=12),
                            ft.Text(f"목표: {item['target_price']:,}원", color=ACCENT_COLOR, size=12, weight="bold")
                        ]),
                        ft.IconButton(icon="delete", icon_color="grey", on_click=lambda e, i=idx: delete_wishlist(i))
                    ], alignment="spaceBetween"),
                    bgcolor=CARD_COLOR, padding=15, border_radius=15
                )
            )
        page.update()

    def delete_wishlist(index):
        del my_wishlist[index]
        save_data()
        refresh_wishlist_tab()

    # --- 메인 탭바 ---
    tabs = ft.Tabs(
        selected_index=0, divider_color="transparent", indicator_color=ACCENT_COLOR, label_color=ACCENT_COLOR,
        unselected_label_color="grey",
        tabs=[ft.Tab(icon="search", text="검색"), ft.Tab(icon="favorite", text="찜 목록"),
              ft.Tab(icon="settings", text="설정")],
        on_change=lambda e: refresh_wishlist_tab()
    )

    content_area = ft.Container(expand=True)

    def on_tab_click(e):
        idx = tabs.selected_index
        content_area.content = [
            ft.Container(content=ft.Column([search_panel, lv_results])),
            lv_wishlist_tab,
            ft.Container(content=settings_view, padding=20)
        ][idx]
        page.update()

    tabs.on_change = on_tab_click

    page.add(
        ft.Stack([
            ft.Column([header, ft.Container(content=tabs, bgcolor=BG_COLOR), ft.Divider(height=1, color="#333"),
                       content_area], expand=True),
            loading_overlay
        ], expand=True)
    )

    on_tab_click(None)
    refresh_wishlist_tab()


ft.app(target=main)