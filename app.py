import datetime
import json
import re
from io import BytesIO
import streamlit as st
from docxtpl import DocxTemplate
from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


# ------------------------- Настройки страницы -------------------------
# Возвращаем "фиксированную" (центрированную) ширину
st.set_page_config(page_title="Генератор офферов", page_icon="📝", layout="centered")

# Глобальный CSS для уменьшения шрифта метрик в expander "Подробнее о доходе" (специфично для BM-структуры)
st.markdown(
    """
    <style>
    /* Селектор для всех "Подробнее о доходе" (expander) — уменьшение размера метрик только внутри них! */
    div[data-testid="stExpander"] .small-metric #bm-metrics [data-testid="stMetric"] {
        font-size: 1.7rem !important;
    }
    div[data-testid="stExpander"] .small-metric #bm-metrics [data-testid="stMetricValue"] {
        font-size: 1.7rem !important;
    }
    div[data-testid="stExpander"] .small-metric #bm-metrics [data-testid="stMetricLabel"] {
        font-size: 1.7rem !important;
    }
    /* Селектор на случай кастомных вложенных стилей Streamlit */
    div[data-testid="stExpander"] .small-metric #bm-metrics .st-emotion-cache-p38tq1 {
        font-size: 1.7rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Компактные стили: метрики, заголовки, подписи и аккуратные инлайн-ошибки
st.markdown(
    """
    <style>
    ul { list-style-type: disc !important; }
    /* Компактные метрики и заголовки */
    [data-testid="stMetric"] { font-size: 0.5rem !important; }
    h1, h2, h3 { margin-bottom: 0.5rem; }
    .stAlert { margin-top: 0.5rem; padding: 0.5rem; }
    .stTextInput > div > div > input { padding: 0.5rem; }
    .stSelectbox > div > div > select { padding: 0.5rem; }
    .small-error{
    color:#d00 !important;      /* красный */
    font-size:0.8rem !important;/* мелкий */
    text-align:left;           /* вправо в своей колонке */
    margin-top:-0.3rem;
    }
    .small-metric-values [data-testid="stMetricValue"] {
        font-size: 0.8rem !important;  /* Уменьшаем до 0.9rem (или меньше, напр. 0.8rem) */
    }
    .small-metric [data-testid="stMetric"] { font-size: 0.9rem; } /* Уменьшенный шрифт для метрик в expander */
    .mbo-tooltip {
        position: relative;
        display: inline-block;
        cursor: pointer;
        transition: color 0.2s ease;
    }
    .mbo-tooltip:hover {
        color: #1f77b4 !important; /* Цвет акцента, например синий */
    }
    .mbo-tooltip .tooltiptext {
        visibility: hidden;
        width: 120px;
        background-color: #333;
        color: #fff;
        text-align: center;
        border-radius: 4px;
        padding: 5px;
        position: absolute;
        z-index: 1;
        bottom: 125%; /* Расположение подсказки сверху */
        left: 50%;
        margin-left: -60px;
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 12px;
        pointer-events: none;
    }
    .mbo-tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
    .mbo-tooltip .tooltiptext::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #333 transparent transparent transparent;
    }
    .preview-container {
    background-color: white !important;
    color: #333333 !important;
    font-family: Arial, sans-serif !important;
    font-size: 14px !important;
    line-height: 1.2 !important;  /* Ещё меньший интервал для сжатия пустых строк */
    padding: 15px !important;   /* Уменьшенный padding */
    border: 1px solid #ddd !important;
    border-radius: 5px !important;
    white-space: pre-wrap !important;
    max-height: 500px !important;
    overflow-y: auto !important;
    }
    .preview-container p {
    margin: 4px 0 !important;  /* Минимальный margin для параграфов, чтобы пустые строки не растягивались */
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <style>
    /* Цвет плейсхолдера для обязательных полей (светло-красный) */
    /* Таргетируем по data-testid и ключам ваших виджетов */
    [data-testid="stTextInput"] input[placeholder="Обязательное поле"]::placeholder {
        color: #e57373 !important;   /* light red */
        opacity: 1 !important;       /* чтобы цвет был заметен */
    }
    [data-testid="stTextArea"] textarea[placeholder="Обязательное поле"]::placeholder {
        color: #e57373 !important;
        opacity: 1 !important;
    }

    /* Цвет плейсхолдера для необязательных полей (светло-зеленый) */
    [data-testid="stTextInput"] input[placeholder="Необязательно поле"]::placeholder {
        color: #81c784 !important;   /* light green */
        opacity: 1 !important;
    }
    [data-testid="stTextArea"] textarea[placeholder="Необязательно поле"]::placeholder {
        color: #81c784 !important;
        opacity: 1 !important;
    }

    /* Дополнительно: Safari/WebKit префиксы (кроссбраузерность) */
    [data-testid="stTextInput"] input[placeholder="Обязательное поле"]::-webkit-input-placeholder { color: #e57373 !important; }
    [data-testid="stTextArea"] textarea[placeholder="Обязательное поле"]::-webkit-input-placeholder { color: #e57373 !important; }
    [data-testid="stTextInput"] input[placeholder="Необязательно поле"]::-webkit-input-placeholder { color: #81c784 !important; }
    [data-testid="stTextArea"] textarea[placeholder="Необязательно поле"]::-webkit-input-placeholder { color: #81c784 !important; }

    /* Firefox префиксы */
    [data-testid="stTextInput"] input[placeholder="Обязательное поле"]::-moz-placeholder { color: #e57373 !important; opacity: 1 !important; }
    [data-testid="stTextArea"] textarea[placeholder="Обязательное поле"]::-moz-placeholder { color: #e57373 !important; opacity: 1 !important; }
    [data-testid="stTextInput"] input[placeholder="Необязательно поле"]::-moz-placeholder { color: #81c784 !important; opacity: 1 !important; }
    [data-testid="stTextArea"] textarea[placeholder="Необязательно поле"]::-moz-placeholder { color: #81c784 !important; opacity: 1 !important; }

    /* Edge/IE старые (на всякий случай) */
    [data-testid="stTextInput"] input[placeholder="Обязательное поле"]:-ms-input-placeholder { color: #e57373 !important; }
    [data-testid="stTextArea"] textarea[placeholder="Обязательное поле"]:-ms-input-placeholder { color: #e57373 !important; }
    [data-testid="stTextInput"] input[placeholder="Необязательно поле"]:-ms-input-placeholder { color: #81c784 !important; }
    [data-testid="stTextArea"] textarea[placeholder="Необязательно поле"]:-ms-input-placeholder { color: #81c784 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <style>
    /* Стили для красных звездочек обязательных полей */
    .required-field-label {
        color: #333;
        margin-bottom: 0.25rem;
        font-size: 0.9rem;
    }
    .required-field-label .required-asterisk {
        color: #ff4444 !important;
        font-weight: bold;
        margin-left: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------- Кэш морфоанализатора -------------------------
@st.cache_resource
def get_morph():
    import pymorphy3
    return pymorphy3.MorphAnalyzer()

# ------------------------- Расчеты дохода -------------------------
def calculate_ndfl(year_income: float) -> float:
    """ Прогрессивная шкала НДФЛ (приближенно), считается по годовому доходу. Возвращает сумму НДФЛ за год. """
    brackets = [
        (2_400_000, 0.13),
        (5_000_000, 0.15),
        (20_000_000, 0.18),
        (50_000_000, 0.20),
        (float("inf"), 0.22),
    ]
    left = float(year_income)
    last_limit = 0.0
    ndfl = 0.0
    for limit, rate in brackets:
        income_in_bracket = min(left, limit - last_limit)
        if income_in_bracket <= 0:
            break
        ndfl += income_in_bracket * rate
        left -= income_in_bracket
        last_limit = limit
    return ndfl

def gross_to_net(gross_salary: float, gross_bonus: float) -> dict:
    """ Конвертация гросс → нетто: - Эффективный НДФЛ считается от годовой суммы; - Нетто-месяц = round(нетто-год / 12); - Оклад/премия в нетто разносятся пропорционально их долям в гросс, при этом сумма нетто-оклад + нетто-премия = нетто-месяц (за счет округления последней части). """
    gross_month = float(gross_salary) + float(gross_bonus)
    gross_year = gross_month * 12.0
    ndfl_year = calculate_ndfl(gross_year) if gross_year > 0 else 0.0
    ndfl_percent_eff = (ndfl_year / gross_year * 100.0) if gross_year > 0 else 0.0
    net_year = gross_year - ndfl_year
    net_month = int(round(net_year / 12.0)) if gross_year > 0 else 0
    if gross_month > 0:
        share_salary = (gross_salary / gross_month) if gross_month else 0.0
        net_salary = int(round(net_month * share_salary))
        net_bonus = int(net_month - net_salary)  # гарантируем точную сумму
        percent_salary = int(round(share_salary * 100))
        percent_bonus = 100 - percent_salary
    else:
        net_salary = 0
        net_bonus = 0
        percent_salary = 0
        percent_bonus = 0
    return dict(
        gross_salary=int(round(gross_salary)),
        gross_bonus=int(round(gross_bonus)),
        gross_month=int(round(gross_month)),
        gross_year=int(round(gross_year)),
        net_salary=net_salary,
        net_bonus=net_bonus,
        net_month=int(round(net_month)),
        net_year=int(round(net_year)),
        ndfl_percent=ndfl_percent_eff,
        percent_salary=percent_salary,
        percent_bonus=percent_bonus,
    )

def gross_to_net_with_bm(gross_salary: float, gross_mbo: float, gross_bm: float) -> dict:
    """ Расчет net для структуры с BM: НДФЛ от полного дохода, net распределяется пропорционально. """
    full_gross_month = float(gross_salary) + float(gross_mbo) + float(gross_bm)
    full_gross_year = full_gross_month * 12.0
    ndfl_year = calculate_ndfl(full_gross_year) if full_gross_year > 0 else 0.0
    ndfl_percent_eff = (ndfl_year / full_gross_year * 100.0) if full_gross_year > 0 else 0.0
    full_net_year = full_gross_year - ndfl_year
    full_net_month = int(round(full_net_year / 12.0)) if full_gross_year > 0 else 0

    if full_gross_month > 0:
        share_salary = gross_salary / full_gross_month
        share_mbo = gross_mbo / full_gross_month
        share_bm = gross_bm / full_gross_month
        net_salary = int(round(full_net_month * share_salary))
        net_mbo = int(round(full_net_month * share_mbo))
        net_bm = int(round(full_net_month * share_bm))
        # Корректировка для точной суммы
        net_mbo += full_net_month - (net_salary + net_mbo + net_bm)  # Корректируем на остаток
    else:
        net_salary = net_mbo = net_bm = 0

    percent_salary = int(round((gross_salary / full_gross_month) * 100)) if full_gross_month > 0 else 0
    percent_mbo = int(round((gross_mbo / full_gross_month) * 100)) if full_gross_month > 0 else 0
    percent_bm = int(round((gross_bm / full_gross_month) * 100)) if full_gross_month > 0 else 0

    return dict(
        gross_salary=int(round(gross_salary)),
        gross_mbo=int(round(gross_mbo)),
        gross_bm=int(round(gross_bm)),
        gross_oklad_mbo=int(round(gross_salary + gross_mbo)),
        full_gross_month=int(round(full_gross_month)),
        full_gross_year=int(round(full_gross_year)),
        net_salary=net_salary,
        net_mbo=net_mbo,
        net_bm=net_bm,
        net_oklad_mbo=net_salary + net_mbo,
        full_net_month=full_net_month,
        full_net_year=int(round(full_net_year)),
        ndfl_percent=ndfl_percent_eff,
        percent_salary=percent_salary,
        percent_mbo=percent_mbo,
        percent_bm=percent_bm,
    )


def recalc_from_percent(percent_salary: int, percent_bonus: int, gross_month: int | float) -> dict:
    """ Пересчет всех метрик из total gross_month + заданная доля оклада/премии. """
    gs = float(gross_month) * (percent_salary / 100.0)
    gb = float(gross_month) * (percent_bonus / 100.0)
    return gross_to_net(gs, gb)

# ------------------------- Вспомогательные функции -------------------------

def compute_form_signature():
    """
    Строит кортеж из исходных значений виджетов, влияющих на оффер.
    Любое изменение подписи => сброс предпросмотра и файла.
    """
    return (
        # Персональные данные
        st.session_state.get("name_input", ""),
        st.session_state.get("surname_input", ""),
        st.session_state.get("gender_input", ""),
        st.session_state.get("genitive_name_input", ""),
        st.session_state.get("position_input", ""),
        # Подразделение (видимое имя и путь)
        selected_dept_display if "selected_dept_display" in locals() else st.session_state.get("selected_dept_display", None),
        department if "department" in locals() else st.session_state.get("department", None),
        # Обязанности (исходный текст из text_area)
        duties_trial_text if "duties_trial_text" in locals() else st.session_state.get("duties_trial_text", ""),
        duties_text if "duties_text" in locals() else st.session_state.get("duties_text", ""),
        # Компенсация / настройка дохода (слайдер и переключатели)
        st.session_state.get("gross_month", 0),
        st.session_state.get("mbo_frequency", "Ежемесячно"),
        st.session_state.get("bonus_on_trial", True),
        st.session_state.get("percent_salary", 0),
        # Гео и формат работы
        city if "city" in locals() else st.session_state.get("city", ""),
        hybrid_mode if "hybrid_mode" in locals() else st.session_state.get("hybrid_mode", True),
        # Рекрутер
        recruiter_name if "recruiter_name" in locals() else st.session_state.get("recruiter_name", ""),
    )


def format_num(num) -> str:
    try:
        return f"{int(num):,}".replace(",", " ")
    except Exception:
        return str(num)

def load_json(filename: str):
    try:
        with open(filename, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Ошибка чтения {filename}: {e}")
        st.stop()

def get_department_options(structure: dict) -> list[tuple[str, str]]:
    """ Возвращает плоский список: - display_name (как показывать) - full_path (полный путь с родителями) """
    options: list[tuple[str, str]] = []

    def traverse(dept_data, parent_path: str = ""):
        if isinstance(dept_data, str):
            full_path = f"{parent_path} / {dept_data}" if parent_path else dept_data
            display_name = f"{dept_data} ({parent_path})" if parent_path else dept_data
            options.append((display_name, full_path))
            return
        dept_name = dept_data.get("name", "")
        new_parent = f"{parent_path} / {dept_name}" if parent_path else dept_name
        display_name = dept_name
        options.append((display_name, new_parent))
        for _, sub in dept_data.get("subdivisions", {}).items():
            traverse(sub, new_parent)

    for _, top in structure.items():
        traverse(top)
    return options

def clean_filename(s: str) -> str:
    s = re.sub(r'[<>:\"/\\|?*]', "", s or "")
    return s.replace(" ", "_")
def sanitize_for_filename(text: str) -> str:
    """
    Преобразует произвольную строку в безопасную для имени файла:
    - заменяет пробелы на подчеркивания,
    - удаляет недопустимые символы,
    - схлопывает повторяющиеся подчеркивания.
    """
    t = (text or "").strip()
    t = t.replace(" ", "_")
    t = re.sub(r'[<>:"/\\|?*\r\n\t]', "", t)
    t = re.sub(r"_+", "_", t)
    return t
def format_position(position: str) -> str:
    # Чтобы не ломать аббревиатуры вроде .NET, QA и пр., не меняем регистр внутри слов,
    # только первую букву первого слова.
    words = (position or "").strip().split()
    if not words:
        return ""
    first = words[0][:1].upper() + words[0][1:]
    return " ".join([first] + words[1:])

def validate_position(position: str) -> tuple[bool, str]:
    if not (position or "").strip():
        return False, "Поле 'Должность' не может быть пустым."
    # Разрешим точки, # и + для .NET / FA# / C++ и пр.
    if not re.match(r"^[а-яА-Яa-zA-Z0-9\s\-+#.\(\)/]+$", position):
        return False, "Должность может содержать буквы, цифры и символы . + # - / ( )"
    return True, ""

def detect_gender(first_name: str, last_name: str) -> str:
    """ Пытается определить пол по имени/фамилии. Возвращает 'М' или 'Ж'. """
    morph = get_morph()
    parses = []
    if first_name:
        parses.append(morph.parse(first_name)[0])
    if last_name:
        parses.append(morph.parse(last_name)[0])
    for p in parses:
        if "Name" in p.tag or "Surn" in p.tag:
            if "masc" in p.tag:
                return "М"
            if "femn" in p.tag:
                return "Ж"
    return "М"

def to_genitive(first_name: str, last_name: str, gender: str) -> str:
    morph = get_morph()
    gender_code = "masc" if gender == "М" else "femn"
    name_g = (first_name or "").capitalize()
    surname_g = (last_name or "").capitalize()
    if first_name:
        np = morph.parse(first_name)[0]
        ng = np.inflect({"gent", gender_code}) if np else None
        if ng:
            name_g = ng.word.capitalize()
    if last_name:
        sp = morph.parse(last_name)[0]
        sg = sp.inflect({"gent", gender_code}) if sp else None
        if sg:
            surname_g = sg.word.capitalize()
    return f"{name_g} {surname_g}".strip()

def format_duties_for_list(duties_text: str) -> list[str]:
    """ Превращает многострочный ввод в список маркеров: - убирает лишние префиксы (цифры/символы), - нормализует регистр, - добавляет ; между пунктами и . в конце. """
    lines = [line.strip() for line in (duties_text or "").replace("\r", "").split("\n")]
    lines = [line for line in lines if line]
    formatted = []
    for i, line in enumerate(lines):
        cleaned_line = re.sub(r"^[\d\s\W_]+", "", line)
        if not cleaned_line:
            continue
        if len(cleaned_line) > 1:
            cleaned_line = cleaned_line[0].upper() + cleaned_line[1:]
        else:
            cleaned_line = cleaned_line.upper()
        if cleaned_line and cleaned_line[-1] in ";.,":  # убрать лишний финальный знак
            cleaned_line = cleaned_line[:-1]
        cleaned_line += ";" if i < len(lines) - 1 else "."
        formatted.append(cleaned_line)
    return formatted

# ------------------------- Функция предпросмотра -------------------------
def generate_text_preview(context: dict) -> str:
    """
    Генерирует HTML-предпросмотр оффера на основе рендеринга шаблона DOCX.
    Извлекает текст с поддержкой жирного выделения, пустых строк, маркированных списков и отступов.
    """
    try:
        # Рендерим шаблон в память
        doc = DocxTemplate("template.docx")
        doc.render(context)
        bio = BytesIO()
        doc.save(bio)
        bio.seek(0)

        # Загружаем сгенерированный DOCX и извлекаем текст с форматированием
        rendered_doc = Document(bio)
        preview_html_parts = []
        in_list = False

        def runs_to_html(runs):
            result = []
            buffer = []
            buffer_bold = None

            def flush_buffer():
                if not buffer:
                    return
                text = "".join(buffer)
                if buffer_bold:
                    result.append(f"<b>{text}</b>")
                else:
                    result.append(text)

            for run in runs:
                text = run.text
                if not text:
                    continue
                bold = run.bold is True

                if buffer_bold is None:
                    buffer_bold = bold

                if bold != buffer_bold:
                    flush_buffer()
                    buffer = [text]
                    buffer_bold = bold
                else:
                    if buffer and not buffer[-1].endswith(" ") and not text.startswith(" "):
                        buffer.append(" ")
                    buffer.append(text)

            flush_buffer()
            return "".join(result).strip()

        for para in rendered_doc.paragraphs:
            if not para.text.strip():
                if not in_list:
                    preview_html_parts.append("<br>")
                continue

            is_bullet = para.style.name.lower().startswith("list bullet")

            line_text = runs_to_html(para.runs)

            if is_bullet:
                if not in_list:
                    preview_html_parts.append("<ul style='list-style-type: disc; list-style-position: inside; padding-left: 20px;'>")
                    in_list = True
                preview_html_parts.append(f"<li>{line_text}</li>")
            else:
                if in_list:
                    preview_html_parts.append("</ul>")
                    in_list = False
                preview_html_parts.append(f'<p style="margin: 4px 0; font-size: 14px;">{line_text}</p>')

        if in_list:
            preview_html_parts.append("</ul>")

        # Добавляем рамки для предпросмотра (с нормальным шрифтом)
        preview_html = [
            '<div style="text-align: center; font-weight: bold; font-size: 16px;">' + "=" * 60 + "</div>",
            '<div style="text-align: center; font-weight: bold; font-size: 14px;">ПРЕДПРОСМОТР ОФФЕРА (НА ОСНОВЕ ШАБЛОНА)</div>',
            '<div style="text-align: center; font-weight: bold; font-size: 16px;">' + "=" * 60 + "</div>",
            "<br>"
        ] + preview_html_parts + [
            "<br>",
            '<div style="text-align: center; font-weight: bold; font-size: 16px;">' + "=" * 60 + "</div>",
            '<div style="text-align: center; font-weight: bold; font-size: 14px;">КОНЕЦ ПРЕДПРОСМОТРА</div>',
            '<div style="text-align: center; font-weight: bold; font-size: 16px;">' + "=" * 60 + "</div>"
        ]

        return "".join(preview_html)

    except Exception as e:
        return f'<p style="color: red;">Ошибка генерации предпросмотра: {str(e)}</p>'

# ------------------------- Данные -------------------------
config = load_json("config.json")
cities = load_json("cities.json")
org_structure = load_json("org_structure.json")
typical_duties = load_json("typical_duties.json")

# ------------------------- UI -------------------------
st.title("Генератор офферов")

# --- Служебное состояние генерации/предпросмотра ---
if "offer_docx_bytes" not in st.session_state:
    st.session_state.offer_docx_bytes = None
if "offer_docx_name" not in st.session_state:
    st.session_state.offer_docx_name = None
if "form_signature" not in st.session_state:
    st.session_state.form_signature = None
if "preview_visible" not in st.session_state:
    st.session_state.preview_visible = False
if "preview_html" not in st.session_state:
    st.session_state.preview_html = None
if "clicked_generate" not in st.session_state:
    st.session_state.clicked_generate = False

# Используем session_state для хранения значений
if "percent_salary" not in st.session_state:
    st.session_state.percent_salary = 80
if "gross_month" not in st.session_state:
    st.session_state.gross_month = 100_000
if "bonus_on_trial" not in st.session_state:
    st.session_state.bonus_on_trial = True
if "mbo_frequency" not in st.session_state:
    st.session_state.mbo_frequency = "Ежемесячно"  # Значение по умолчанию
if "income_structure" not in st.session_state:
    st.session_state.income_structure = "Оклад + MBO"  # Значение по умолчанию


st.subheader("Основное")
# 1. Персональные данные (Имя, Фамилия, Пол в одной строке)
col1, col2, col3 = st.columns([0.4, 0.4, 0.2])
with col1:
    st.markdown('<div class="required-field-label">Имя в им. падеже <span class="required-asterisk">*</span></div>', unsafe_allow_html=True)
    name = st.text_input(label="Имя", key="name_input", label_visibility="collapsed")
with col2:
    st.markdown('<div class="required-field-label">Фамилия в им. падеже <span class="required-asterisk">*</span></div>', unsafe_allow_html=True)
    surname = st.text_input(label="Фамилия", key="surname_input", label_visibility="collapsed")
with col3:
    auto_gender = detect_gender(name, surname) if (name or surname) else "М"
    st.markdown('<div class="required-field-label">Пол <span class="required-asterisk">*</span></div>', unsafe_allow_html=True)
    gender = st.radio(label="Пол", options=["М", "Ж"], index=0 if auto_gender == "М" else 1, horizontal=True, key="gender_input",  label_visibility="collapsed")

# Имя/Фамилия в род. падеже и Должность
col4, col5 = st.columns([0.6, 0.4])
with col4:
    st.markdown('<div class="required-field-label">Имя и Фамилия в род. падеже (для «Для ...») <span class="required-asterisk">*</span></div>', unsafe_allow_html=True)
    genitive_name = st.text_input(
    label="Имя дательный", 
    value=to_genitive(name, surname, gender) if (name and surname) else "",
    key="genitive_name_input",
    label_visibility="collapsed",
)
with col5:
    st.markdown('<div class="required-field-label">Должность <span class="required-asterisk">*</span></div>', unsafe_allow_html=True)
    position = st.text_input(label="Должность", key="position_input", label_visibility="collapsed")
    is_valid_position, position_error = validate_position(position)
    # Сообщение об ошибке для поля "Должность" отключено по требованиям
    # if position_error:
    #     st.markdown(
    #         f'<p class="small-error">{position_error}</p>',
    #         unsafe_allow_html=True
    #     )


# 2. Подразделение
dept_options = get_department_options(org_structure)
st.markdown('<div class="required-field-label">Подразделение <span class="required-asterisk">*</span></div>', unsafe_allow_html=True)
selected_dept_display = st.selectbox(label="Подразделение", options=[opt[0] for opt in dept_options], label_visibility="collapsed")
department = next((opt[1] for opt in dept_options if opt[0] == selected_dept_display), "")
st.session_state.selected_dept_display = selected_dept_display
st.session_state.department = department

# 3. Обязанности
st.subheader("Обязанности")

# Выпадающий список типовых обязанностей
typical_duty_names = ["-- Не выбрано --"] + list(typical_duties.keys())
selected_typical_duty = st.selectbox(
    "Типовые обязанности", 
    options=typical_duty_names,
    index=0,
    help="Выберите типовую должность для автозаполнения обязанностей"
)

# Обязанности (в одной строке, двумя колонками, на ИС слева)
col_duties1, col_duties2 = st.columns(2)

# Инициализация значений обязанностей
if "duties_trial_text" not in st.session_state:
    st.session_state.duties_trial_text = ""
if "duties_text" not in st.session_state:
    st.session_state.duties_text = ""

# Автозаполнение при выборе типовых обязанностей
if selected_typical_duty != "-- Не выбрано --":
    duty_data = typical_duties[selected_typical_duty]
    
    # Формируем текст для обязанностей на ИС
    trial_duties_list = duty_data.get("обязанности_на_ис", [])
    if trial_duties_list:
        formatted_trial_duties = "\n".join([f"• {duty}" for duty in trial_duties_list])
        if st.session_state.duties_trial_text != formatted_trial_duties:
            st.session_state.duties_trial_text = formatted_trial_duties
    
    # Формируем текст для основных обязанностей
    main_duties_list = duty_data.get("обязанности", [])
    if main_duties_list:
        formatted_main_duties = "\n".join([f"• {duty}" for duty in main_duties_list])
        if st.session_state.duties_text != formatted_main_duties:
            st.session_state.duties_text = formatted_main_duties

with col_duties1:  # левая колонка
    duties_trial_text = st.text_area(
        "Обязанности на ИС", 
        height=150, 
        placeholder="Необязательно поле",
        value=st.session_state.duties_trial_text
    )
    st.session_state.duties_trial_text = duties_trial_text
    duties_trial = format_duties_for_list(duties_trial_text)

with col_duties2:  # правая колонка
    st.markdown('<div class="required-field-label">Обязанности <span class="required-asterisk">*</span></div>', unsafe_allow_html=True)
    duties_text = st.text_area(
        label="Обязанности", 
        height=150, 
        label_visibility="collapsed",
        value=st.session_state.duties_text
    )
    st.session_state.duties_text = duties_text
    duties = format_duties_for_list(duties_text)

st.subheader("Заработная плата")
income_structure = st.radio(
    "Структура дохода",
    ["Оклад + MBO", "Оклад + MBO + БМ (проектная)", "Оклад / Оклад + БМ"],
    index=0 if st.session_state.income_structure == "Оклад + MBO" else (1 if st.session_state.income_structure == "Оклад + MBO + БМ (проектная)" else 2),
    horizontal=True
)

# Обновляем структуру дохода в session_state
if st.session_state.income_structure != income_structure:
    # При смене структуры устанавливаем процент по умолчанию
    if income_structure == "Оклад + MBO + БМ (проектная)":
        st.session_state.percent_salary = 60
    elif income_structure == "Оклад + MBO":
        st.session_state.percent_salary = 80
    st.session_state.income_structure = income_structure
else:
    st.session_state.income_structure = income_structure


# Инициализация по умолчанию (зависит от структуры)
if income_structure == "Оклад + MBO + БМ (проектная)":
    if "percent_salary" not in st.session_state or st.session_state.income_structure != income_structure:
        st.session_state.percent_salary = 60
elif income_structure == "Оклад + MBO":
    if "percent_salary" not in st.session_state or st.session_state.income_structure != income_structure:
        st.session_state.percent_salary = 80
else:
    if "percent_salary" not in st.session_state:
        st.session_state.percent_salary = 80


# 4. Компенсация
if income_structure == "Оклад / Оклад + БМ":
    col_gm, col_bm = st.columns([7, 2])
elif income_structure in ["Оклад + MBO"]:
    col_gm, col_frequency, col_bonus = st.columns([4, 2, 1])
elif income_structure == "Оклад + MBO + БМ (проектная)":
    col_gm, col_gm_bm, col_bonus = st.columns([7, 7, 2])  # Для BM-структуры: 3 колонки
else:
    col_gm, col_bonus = st.columns([4, 3])


with col_gm:
    if income_structure == "Оклад / Оклад + БМ":
        label = "Оклад (мес.) gross"
    elif income_structure == "Оклад + MBO":
        label = "ЗП в месяц gross"
    else:
        label = "Оклад + MBO (gross)"
    st.session_state.gross_month = st.number_input(label, min_value=0, step=10000, value=st.session_state.gross_month)


# Добавляем новое поле только для структуры "Оклад + MBO + БМ (проектная)"
if income_structure == "Оклад + MBO + БМ (проектная)":
    with col_gm_bm:
        # Инициализация поля в session_state
        if "gross_month_bm_avg" not in st.session_state:
            st.session_state.gross_month_bm_avg = 150_000
        
        # Поле должно быть равно fullgrossmonth - находим его через расчет
        # Берем значения из текущего расчета БМ-структуры
        percent_per_bonus = (100 - st.session_state.percent_salary) / 2.0
        ratio = (st.session_state.percent_salary + percent_per_bonus) / 100.0
        current_fullgross = st.session_state.gross_month / ratio if ratio > 0 else 0
        
        # Устанавливаем значение равным текущему fullgrossmonth
        st.session_state.gross_month_bm_avg = st.number_input(
            "Оклад + MBO + БМ (проектная) (gross)", 
            min_value=0, 
            step=10000, 
            value=int(current_fullgross),
            key="gross_month_bm_avg_input"
        )
        
        # При изменении этого поля пересчитываем основное поле gross_month
        if st.session_state.gross_month_bm_avg != current_fullgross:
            # Пересчитываем gross_month из нового значения средней ЗП
            new_ratio = (st.session_state.percent_salary + percent_per_bonus) / 100.0
            st.session_state.gross_month = int(st.session_state.gross_month_bm_avg * new_ratio)
            st.rerun()

# Новое поле для структуры "Оклад / Оклад + БМ"
if income_structure == "Оклад / Оклад + БМ":
    with col_bm:
        # Инициализация поля БМ в session_state
        if "bm_enabled" not in st.session_state:
            st.session_state.bm_enabled = "Нет"
        
        bm_enabled = st.radio(
            "БМ", 
            ["Да", "Нет"], 
            index=0 if st.session_state.bm_enabled == "Да" else 1,
            horizontal=True
        )
        st.session_state.bm_enabled = bm_enabled

# Отображаем MBO на ИС для всех структур кроме "Оклад / Оклад + БМ"
if income_structure != "Оклад / Оклад + БМ":
    with col_bonus:
        bonus_label = "MBO на ИС"
        bonus_on_trial = st.radio(bonus_label, ["Да", "Нет"], 
                                 index=0 if st.session_state.bonus_on_trial else 1)
        st.session_state.bonus_on_trial = (bonus_on_trial == "Да")

if income_structure == "Оклад + MBO":
    with col_frequency:
        mbo_frequency = st.radio(
            "Выплата MBO",
            ["Ежемесячно", "Ежеквартально"],
            index=0 if st.session_state.mbo_frequency == "Ежемесячно" else 1,
            horizontal=True
        )
        st.session_state.mbo_frequency = mbo_frequency


# Для структуры "Оклад / Оклад + БМ" MBO на ИС всегда Нет
if income_structure == "Оклад / Оклад + БМ":
    st.session_state.bonus_on_trial = False

# Слайдер и быстрые кнопки в одной строке
col_slider_and_buttons = st.columns([7, 1, 1, 1, 1])
with col_slider_and_buttons[0]:
    if income_structure == "Оклад + MBO":
        slider_label = "Оклад/MBO"
        quick_values = [( "60", 60), ("70", 70), ("80", 80), ("90", 90)]
    elif income_structure == "Оклад / Оклад + БМ":
        # Для этой структуры не показываем слайдер и кнопки
        quick_values = []
    else:
        slider_label = "Процент оклада"
        quick_values = [("40", 40), ("50", 50), ("60", 60), ("70", 70)]
    if income_structure != "Оклад / Оклад + БМ":
        percent_salary = st.slider(slider_label, 0, 100, value=st.session_state.percent_salary, step=1)
        st.session_state.percent_salary = percent_salary
    else:
        # Для структуры "Оклад / Оклад + БМ" фиксируем процент на 100
        percent_salary = 100
        st.session_state.percent_salary = percent_salary


def quick_btn(label, value):
    if st.button(label, key=f"btn_{label}"):
        st.session_state.percent_salary = value
        st.rerun()

# оборачиваем каждую группу кнопок в flex-контейнер высотой 100 %
if income_structure != "Оклад / Оклад + БМ":
    for col, (lbl, val) in zip(
            col_slider_and_buttons[1:],
            quick_values + [("80", 80)] if income_structure == "Оклад + MBO + БМ (проектная)" else quick_values):
        with col:
            st.markdown(
                '<div style="display:flex; align-items:flex-end; height:100%;">',
                unsafe_allow_html=True)
            quick_btn(lbl, val)
            st.markdown('</div>', unsafe_allow_html=True)


# Расчет дохода
if income_structure == "Оклад + MBO":
    percent_bonus = 100 - percent_salary
    income = recalc_from_percent(percent_salary, percent_bonus, st.session_state.gross_month)
elif income_structure == "Оклад / Оклад + БМ":
    # Для этой структуры всегда 100% оклад
    income = recalc_from_percent(100, 0, st.session_state.gross_month)

else:  # "Оклад + MBO + БМ (проектная)"
    percent_per_bonus = (100 - percent_salary) / 2.0
    ratio = (percent_salary + percent_per_bonus) / 100.0
    
    # Если установлено поле средней ЗП, используем его как full_gross_month
    if "gross_month_bm_avg" in st.session_state:
        full_gross_month = float(st.session_state.gross_month_bm_avg)
        # Синхронизируем основное поле с новым расчетом
        calculated_gross = full_gross_month * ratio
        if abs(calculated_gross - st.session_state.gross_month) > 1:
            st.session_state.gross_month = int(calculated_gross)
    else:
        full_gross_month = st.session_state.gross_month / ratio if ratio > 0 else 0
    
    gross_salary = full_gross_month * (percent_salary / 100.0)
    gross_mbo = full_gross_month * (percent_per_bonus / 100.0)
    gross_bm = gross_mbo
    st.session_state.mbo_frequency = "Ежемесячно"  # Фиксируем ежемесячно для этой структуры
    income = gross_to_net_with_bm(gross_salary, gross_mbo, gross_bm)


# Раздел ЗП в месяц gross
st.markdown("<h5>Расшифровка дохода (gross)</h5>", unsafe_allow_html=True)
if income_structure == "Оклад + MBO":

    cols = st.columns(5)

    if st.session_state.mbo_frequency == "Ежеквартально":
        display_bonus = income["gross_bonus"] * 3
        bonus_label = "MBO Квартальная"
    else:
        display_bonus = income["gross_bonus"]
        bonus_label = "MBO"

    labels = [
        ("Средняя ЗП (мес.)", income["gross_month"]),
        ("Оклад", income["gross_salary"]),
        (bonus_label, display_bonus),
        ("Оклад/MBO", f"{percent_salary}/{100 - percent_salary}%"),
        ("MBO на ИС", "Да" if st.session_state.bonus_on_trial else "Нет"),
    ]

    for col, (label, value) in zip(cols, labels):
        if label == "MBO Квартальная":
            monthly_bonus = format_num(income['gross_bonus'])
            col.markdown(
                f"""
                <div style='text-align:center; font-size:1.7rem;'>
                    <div style='font-weight:500; font-size:1rem; color:gray'>{label}</div>
                    <div class='mbo-tooltip' style='font-weight:600; cursor:pointer;'>
                        {format_num(value)}
                        <span class='tooltiptext'>{monthly_bonus} × 3</span>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

        else:
            display = f"{value:,}".replace(",", " ") if isinstance(value, (int, float)) else str(value)
            col.markdown(
                f"<div style='text-align:center; font-size:1.7rem;'>"
                f"<div style='font-weight:500; font-size:1rem; color:gray'>{label}</div>"
                f"<div style='font-weight:600;'>{display}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

elif income_structure == "Оклад / Оклад + БМ":
    # Показываем метрики для структуры "Оклад / Оклад + БМ"
    cols = st.columns(4)
    
    # Формируем значение для "Средняя ЗП (мес.)"
    if st.session_state.bm_enabled == "Да":
        avg_salary_display = f"{format_num(income['gross_salary'])} + БМ"
    else:
        avg_salary_display = format_num(income["gross_salary"])
    
    labels = [
        ("Средняя ЗП (мес.)", avg_salary_display),
        ("Оклад", income["gross_salary"]),
        ("БМ", "Да" if st.session_state.bm_enabled == "Да" else "Нет"),
        ("Эффективный НДФЛ", f"{income['ndfl_percent']:.2f}%"),
    ]

    for col, (label, value) in zip(cols, labels):
        if label == "Средняя ЗП (мес.)":
            # Для средней ЗП используем готовое значение
            display = avg_salary_display
        elif label == "Эффективный НДФЛ":
            # Для эффективного НДФЛ используем готовое значение
            display = f"{income['ndfl_percent']:.2f}%"
        else:
            display = f"{value:,}".replace(",", " ") if isinstance(value, (int, float)) else str(value)
        col.markdown(
            f"<div style='text-align:center; font-size:1.7rem;'>"
            f"<div style='font-weight:500; font-size:1rem; color:gray'>{label}</div>"
            f"<div style='font-weight:600;'>{display}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )



else:  # "Оклад + MBO + БМ (проектная)"
    # Всегда monthly для BM-структуры
    display_mbo = income["gross_mbo"]
    mbo_label = "MBO"
    display_bm = income["gross_bm"]
    bm_label = "БМ (проектная)"

    # Первая строка: 4 метрики
    cols1 = st.columns(4)
    labels1 = [
        ("Средняя ЗП (мес.)", income["full_gross_month"]),
        ("MBO на ИС", "Да" if st.session_state.bonus_on_trial else "Нет"),
        ("Пропорция", f"{income['percent_salary']}/{income['percent_mbo']}/{income['percent_bm']}%"),
        ("Эффективный НДФЛ", f"{income['ndfl_percent']:.2f}%"),
    ]
    for col, (label, value) in zip(cols1, labels1):
        display = f"{value:,}".replace(",", " ") if isinstance(value, (int, float)) else str(value)
        col.markdown(
            f"<div style='text-align:center; font-size:1.7rem;'>"
            f"<div style='font-weight:500; font-size:1rem; color:gray'>{label}</div>"
            f"<div style='font-weight:600;'>{display}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Вторая строка: 4 метрики
    cols2 = st.columns(4)
    labels2 = [
        ("Оклад + MBO", income["gross_oklad_mbo"]),
        ("Оклад", income["gross_salary"]),
        (mbo_label, display_mbo),
        (bm_label, display_bm),
    ]
    for col, (label, value) in zip(cols2, labels2):
        display = f"{value:,}".replace(",", " ") if isinstance(value, (int, float)) else str(value)
        col.markdown(
            f"<div style='text-align:center; font-size:1.7rem;'>"
            f"<div style='font-weight:500; font-size:1rem; color:gray'>{label}</div>"
            f"<div style='font-weight:600;'>{display}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


st.markdown("<br>", unsafe_allow_html=True)
# Expander "Подробнее о доходе" с уменьшенным шрифтом метрик
with st.expander("Подробнее о доходе"):
    
    st.markdown('<div class="small-metric">', unsafe_allow_html=True)
    if income_structure == "Оклад + MBO":

        col_d1, col_d2, col_d3 = st.columns(3)

        col_d1.metric("ЗП в месяц на руки", format_num(income["net_month"]))
        col_d2.metric("Оклад на руки", format_num(income["net_salary"]))

        if st.session_state.mbo_frequency == "Ежеквартально":
            bonus_net_quarter = income["net_bonus"] * 3
            bonus_net_monthly = format_num(income["net_bonus"])

            # Кастомный div с заголовком и числом в стиле метрики и с тултипом через CSS
            html_content = f"""
            <div style="text-align:left;"> 
                <div style="font-weight:400; font-size:0.9rem; margin-bottom:0.2rem;">
                    MBO квартальная на руки
                </div>
                <div class="mbo-tooltip" style="font-weight:500; font-size:2.3rem; cursor:pointer; display:flex; align-items:center; justify-content:flex-start; position:relative; height:2.3rem;"> 
                    {format_num(bonus_net_quarter)}
                    <span class="tooltiptext">{bonus_net_monthly} × 3</span>
                </div>
            </div>
            """
            col_d3.markdown(html_content, unsafe_allow_html=True)
        else:
            col_d3.metric("Премия на руки", format_num(income["net_bonus"]))

        col_d4, col_d5, col_d6 = st.columns(3)
        col_d4.metric("Годовой доход gross", format_num(income["gross_year"]))
        col_d5.metric("Годовой доход на руки", format_num(income["net_year"]))
        col_d6.metric("Эффективный НДФЛ", f"{income['ndfl_percent']:.2f}%")
    
    
    elif income_structure == "Оклад / Оклад + БМ":
        col_d1, col_d2, col_d3 = st.columns(3)
        
        col_d1.metric("Оклад (мес) net", format_num(income["net_salary"]))
        col_d2.metric("ЗП (год) gross", format_num(income["gross_year"]))
        col_d3.metric("ЗП (год) net", format_num(income["net_year"]))
       

    
    else:  # "Оклад + MBO + БМ (проектная)"
        
        st.markdown('<div id="bm-metrics">', unsafe_allow_html=True)
        # Первая строка: 4 метрики с маленьким шрифтом
        col1_1, col1_2, col1_3, col1_4 = st.columns(4)
        col1_1.markdown(f'<div style="font-size: 1.7rem; text-align: center;"><p style="font-size: 1rem; color: gray; margin-bottom: 0;">ЗП (мес) net</p><p style="font-size: 1.7rem;">{format_num(income["full_net_month"])}</p></div>', unsafe_allow_html=True)
        col1_2.markdown(f'<div style="font-size: 1.7rem; text-align: center;"><p style="font-size: 1rem; color: gray; margin-bottom: 0;">Оклад+MBO (мес) net</p><p style="font-size: 1.7rem;">{format_num(income["net_oklad_mbo"])}</p></div>', unsafe_allow_html=True)
        col1_3.markdown(f'<div style="font-size: 1.7rem; text-align: center;"><p style="font-size: 1rem; color: gray; margin-bottom: 0;">Оклад (мес) net</p><p style="font-size: 1.7rem;">{format_num(income["net_salary"])}</p></div>', unsafe_allow_html=True)
        col1_4.markdown(f'<div style="font-size: 1.7rem; text-align: center;"><p style="font-size: 1rem; color: gray; margin-bottom: 0;">MBO=БМ (мес) net</p><p style="font-size: 1.7rem;">{format_num(income["net_mbo"])}</p></div>', unsafe_allow_html=True)

        # Вторая строка: 4 метрики с маленьким шрифтом
        col2_1, col2_2, col2_3, col2_4 = st.columns(4)
        col2_1.markdown(f'<div style="font-size: 1.7rem; text-align: center;"><p style="font-size: 1rem; color: gray; margin-bottom: 0;">ЗП (год) gross</p><p style="font-size: 1.7rem;">{format_num(income["full_gross_year"])}</p></div>', unsafe_allow_html=True)
        col2_2.markdown(f'<div style="font-size: 1.7rem; text-align: center;"><p style="font-size: 1rem; color: gray; margin-bottom: 0;">ЗП (год) net</p><p style="font-size: 1.7rem;">{format_num(income["full_net_year"])}</p></div>', unsafe_allow_html=True)
        col2_3.markdown(f'<div style="font-size: 1.7rem; text-align: center;"><p style="font-size: 0.95rem; color: gray; margin-bottom: 0;">Оклад+MBO (год) gross</p><p style="font-size: 1.7rem;">{format_num(income["gross_oklad_mbo"] * 12)}</p></div>', unsafe_allow_html=True)
        col2_4.markdown(f'<div style="font-size: 1.7rem; text-align: center;"><p style="font-size: 1rem; color: gray; margin-bottom: 0;">Оклад+MBO (год) net</p><p style="font-size: 1.7rem;">{format_num(income["net_oklad_mbo"] * 12)}</p></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)




# 5. Город и рекрутер
st.subheader("Город и рекрутер")

# Две равные колонки (по 50% ширины)
col_city, col_recruiter = st.columns(2)

with col_city:
    city = st.selectbox("Город", list(cities.keys()))

with col_recruiter:
    recruiters = config["recruiters"]
    recruiter_name = st.selectbox("Рекрутер", [r["name"] for r in recruiters])

# Чекбокс "Гибрид" - показывается только когда город не "Дистант"
hybrid_mode = True  # По умолчанию включен
if city != "Дистант":
    hybrid_mode = st.checkbox(
        "Гибрид (дистанционная работа до 80%)",
        value=True,
        help="Возможность дистанционной работы до 80% рабочего времени"
    )
st.session_state.city = city
st.session_state.recruiter_name = recruiter_name
st.session_state.hybrid_mode = hybrid_mode

# Деривативы выбора города/рекрутера
city_data = cities.get(city, {})
address = city_data.get("address", "")
bonus_health = city_data.get("bonus_health", "")
is_remote = city == "Дистант"

recruiter = next((r for r in recruiters if r["name"] == recruiter_name), {})

# --- Автосброс предпросмотра и файла при любых изменениях в форме ---
current_signature = compute_form_signature()
if st.session_state.form_signature is None:
    st.session_state.form_signature = current_signature
else:
    if current_signature != st.session_state.form_signature:
        # Данные изменились — скрываем предпросмотр и сбрасываем файл/HTML
        st.session_state.preview_visible = False
        st.session_state.offer_docx_bytes = None
        st.session_state.offer_docx_name = None
        st.session_state.preview_html = None
        st.session_state.form_signature = current_signature


# 6. Генерация оффера
st.subheader("Генерация")

# Проверяем заполненность обязательных полей
can_generate = bool(name and surname and position and is_valid_position and genitive_name)
generate_clicked = False

# Две колонки под кнопки (по 50% ширины)
col_left, col_right = st.columns(2)

with col_left:
    if not can_generate:
        st.warning("⚠️ Заполните все обязательные поля для генерации оффера")
    else:
        st.button(
            "🛠️ Сгенерировать оффер",
            use_container_width=True,
            on_click=lambda: st.session_state.update({"clicked_generate": True})
            )

# Если был клик — готовим контекст, генерируем предпросмотр и DOCX в фоне
if st.session_state.get("clicked_generate"):
        # Подготавливаем данные для шаблона
    if income_structure == "Оклад + MBO":
        template_bonus = income["gross_bonus"]
        bonus_period_text = "Ежемесячная"
        if st.session_state.mbo_frequency == "Ежеквартально":
            template_bonus = income["gross_bonus"] * 3
            bonus_period_text = "Ежеквартальная"

        context = {
            "ИФ_род": genitive_name,
            "Дата": datetime.date.today().strftime("%d.%m.%Y"),
            "Пол_падеж": "ый" if gender == "М" else "ая",
            "Имя": name,
            "Должность": format_position(position),
            "Подразделение": department,
            "Обязанности": duties,
            "Обязанности_на_ИС": duties_trial,
            "Оклад": format_num(income["gross_salary"]),
            "Премия": format_num(template_bonus),
            "Премия_период": bonus_period_text,
            # Общий доход
            "Месячный_доход": format_num(income["gross_month"]),
            "Квартальный_доход": format_num(income["gross_month"] * 3),
            "Процент_оклада": percent_salary,
            "Процент_премии": 100 - percent_salary,
            # Доход на испытании (без премии)
            "Квартальный_доход_ИС": format_num(income["gross_salary"] * 3) if not st.session_state.bonus_on_trial else "",
            "Месячный_доход_ИС": format_num(income["gross_salary"]) if not st.session_state.bonus_on_trial else "",
            "Процент_оклада_ИС": 100 if not st.session_state.bonus_on_trial else "",
            # Доход по результатам испытания (с премией)
            "Квартальный_доход_после_ИС": format_num(income["gross_month"] * 3) if not st.session_state.bonus_on_trial else "",
            "Месячный_доход_после_ИС": format_num(income["gross_month"]) if not st.session_state.bonus_on_trial else "",
            "Процент_оклада_после_ИС": percent_salary if not st.session_state.bonus_on_trial else "",
            "Процент_премии_после_ИС": 100 - percent_salary if not st.session_state.bonus_on_trial else "",
            # Блоки отображения
            "Блок_с_премией_на_ИС": st.session_state.bonus_on_trial,
            "Блок_без_премии_на_ИС": not st.session_state.bonus_on_trial,
            # Геолокация и условия работы
            "Дистант": is_remote,
            "Город": not is_remote,
            "Адрес_офиса": address,
            "Гибрид": hybrid_mode and not is_remote,
            "Бонусы_ЗОЖ": bonus_health,
            # Рекрутер
            "Должность_рекрутера_дательный": recruiter.get("position_dative", ""),
            "Рекрутер_дательный": recruiter.get("name_dative", ""),
            "Телефон_рекрутера": recruiter.get("phone", ""),
            "Email_рекрутера": recruiter.get("email", ""),
            # Новые для BM (пустые)
            "Блок_с_БМ": False,
            "БМ": "",
            "Процент_БМ_после_ИС": "",
        }
    
    elif income_structure == "Оклад / Оклад + БМ":
        # Для структуры "Оклад / Оклад + БМ"
        context = {
            "ИФ_род": genitive_name,
            "Дата": datetime.date.today().strftime("%d.%m.%Y"),
            "Пол_падеж": "ый" if gender == "М" else "ая",
            "Имя": name,
            "Должность": format_position(position),
            "Подразделение": department,
            "Обязанности": duties,
            "Обязанности_на_ИС": duties_trial,
            "Оклад": format_num(income["gross_salary"]),
            # Общий доход
            "Месячный_доход": format_num(income["gross_month"]),
            "Квартальный_доход": format_num(income["gross_month"] * 3),
            # БМ данные
            "БМ_включена": st.session_state.bm_enabled == "Да",
            # Блоки отображения - новый блок для структуры "Оклад / Оклад + БМ"
            "Блок_Оклад_БМ": True,
            "Блок_с_БМ": False,  # Отключаем старый БМ блок
            "Блок_с_премией_на_ИС": False,  # MBO отсутствует
            "Блок_без_премии_на_ИС": False,  # MBO отсутствует
            # Геолокация и условия работы
            "Дистант": is_remote,
            "Город": not is_remote,
            "Адрес_офиса": address,
            "Гибрид": hybrid_mode and not is_remote,
            "Бонусы_ЗОЖ": bonus_health,
            # Рекрутер
            "Должность_рекрутера_дательный": recruiter.get("position_dative", ""),
            "Рекрутер_дательный": recruiter.get("name_dative", ""),
            "Телефон_рекрутера": recruiter.get("phone", ""),
            "Email_рекрутера": recruiter.get("email", ""),
        }

    
    else:  # "Оклад + MBO + БМ (проектная)"
        
        bonus_period_text = "Ежемесячная"
        template_mbo = income["gross_mbo"]  # Всегда monthly
        template_bm = income["gross_bm"]  # BM monthly

            # Инициализируем переменные для предотвращения NameError
        monthly_income_IS = 0
        quarterly_income_IS = 0
        income_IS_parts = []
        monthly_income_after = 0
        quarterly_income_after = 0
        income_after_parts = []

        # На ИС: оклад + MBO (если да), без BM и без процентов
        if st.session_state.bonus_on_trial:
                monthly_income_IS = income["gross_oklad_mbo"]
                quarterly_income_IS = monthly_income_IS * 3
                income_IS_parts = [
                    f"Оклад: {format_num(income['gross_salary'])} руб.",
                    f"{bonus_period_text} премия МВО: {format_num(template_mbo)} руб."
                ]
        else:
                monthly_income_IS = income["gross_salary"]
                quarterly_income_IS = monthly_income_IS * 3
                income_IS_parts = [f"Оклад: {format_num(income['gross_salary'])} руб."]
        # По результатам: оклад [%], MBO [%], BM [%]
        monthly_income_after = income["full_gross_month"]
        quarterly_income_after = monthly_income_after * 3
        income_after_parts = [
                f"Оклад: {format_num(income['gross_salary'])} руб. [{income['percent_salary']}%]",
                f"{bonus_period_text} премия МВО: {format_num(template_mbo)} руб. [{income['percent_mbo']}%]",
                f"БМ (бизнес-мотивация) проектная: {format_num(template_bm)} руб. [{income['percent_bm']}%]",
        ]


        context = {
            "ИФ_род": genitive_name,
            "Дата": datetime.date.today().strftime("%d.%m.%Y"),
            "Пол_падеж": "ый" if gender == "М" else "ая",
            "Имя": name,
            "Должность": format_position(position),
            "Подразделение": department,
            "Обязанности": duties,
            "Обязанности_на_ИС": duties_trial,
            # Для новой структуры
            "Блок_с_БМ": True,
            "Блок_с_премией_на_ИС": st.session_state.bonus_on_trial,  # Для MBO на ИС
            "Блок_без_премии_на_ИС": not st.session_state.bonus_on_trial,
            "Квартальный_доход_ИС": format_num(quarterly_income_IS),
            "Месячный_доход_ИС": format_num(monthly_income_IS),
            "Income_IS_Parts": income_IS_parts,  # Список строк для ИС (без %)
            "Квартальный_доход_после_ИС": format_num(quarterly_income_after),
            "Месячный_доход_после_ИС": format_num(monthly_income_after),
            "Income_After_Parts": income_after_parts,  # Список строк с %
            "Премия_период": bonus_period_text,
            # Геолокация и условия работы
            "Дистант": is_remote,
            "Город": not is_remote,
            "Адрес_офиса": address,
            "Гибрид": hybrid_mode and not is_remote,
            "Бонусы_ЗОЖ": bonus_health,
            # Рекрутер
            "Должность_рекрутера_дательный": recruiter.get("position_dative", ""),
            "Рекрутер_дательный": recruiter.get("name_dative", ""),
            "Телефон_рекрутера": recruiter.get("phone", ""),
            "Email_рекрутера": recruiter.get("email", ""),
        }

    
    # Генерация предпросмотра и сохранение в состояние
    preview_html = generate_text_preview(context)
    st.session_state.preview_html = preview_html

    # Генерация DOCX в фоне и сохранение в session_state
    try:
        doc = DocxTemplate("template.docx")
        doc.render(context)
        bio = BytesIO()
        doc.save(bio)
        bio.seek(0)
        st.session_state.offer_docx_bytes = bio.getvalue()
        # Имя файла по шаблону: ггггммдд_Job_Offer_Фамилия_Имя_Должность.docx
        today_str = datetime.date.today().strftime("%Y%m%d")
        safe_surname = sanitize_for_filename(surname)
        safe_name = sanitize_for_filename(name)
        safe_position = sanitize_for_filename(format_position(position))
        st.session_state.offer_docx_name = f"{today_str}_Job_Offer_{safe_surname}_{safe_name}_{safe_position}.docx"

    except Exception as e:
        st.error(f"❌ Ошибка при создании документа: {str(e)}")
        st.session_state.offer_docx_bytes = None
        st.session_state.offer_docx_name = None

    # Фиксируем состояние после генерации и сбрасываем флаг клика
    st.session_state.preview_visible = True
    st.session_state.form_signature = compute_form_signature()
    st.session_state.clicked_generate = False


# Показать кнопку скачивания в правой колонке, если файл готов
with col_right:
    offer_bytes = st.session_state.get("offer_docx_bytes")
    offer_name = st.session_state.get("offer_docx_name", "Offer.docx")
    if offer_bytes and st.session_state.preview_visible:
        st.download_button(
            label="📥 Скачать DOCX",
            data=offer_bytes,
            file_name=offer_name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

# Предпросмотр (оставляем ниже кнопок)
if st.session_state.preview_visible and st.session_state.get("offer_docx_bytes") and st.session_state.get("preview_html"):
    st.markdown("---")
    st.subheader("📄 Предпросмотр оффера")
    st.markdown("**Текст оффера (предварительная версия)**")
    st.markdown(f'<div class="preview-container">{st.session_state.preview_html}</div>', unsafe_allow_html=True)
    st.caption("Это предварительная текстовая версия. Финальная версия с правильным форматированием доступна в DOCX файле.")
