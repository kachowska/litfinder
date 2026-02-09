"""
LitFinder Telegram Bot
Academic literature search via Telegram
Built with aiogram 3.x
"""
import asyncio
import logging
from typing import Optional
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- FSM States ---

class SearchStates(StatesGroup):
    """Finite state machine for search flow."""
    waiting_query = State()
    viewing_results = State()
    selecting_articles = State()
    generating_bibliography = State()


# --- Router ---

router = Router()


# --- Keyboards ---

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск статей", callback_data="search")],
        [InlineKeyboardButton(text="📚 Мои списки", callback_data="my_lists")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])


def search_results_keyboard(articles: list, page: int = 0) -> InlineKeyboardMarkup:
    """Keyboard with search results."""
    buttons = []
    
    # Article buttons (max 5 per page)
    for i, article in enumerate(articles[page*5:(page+1)*5], 1):
        title = article.get("title", "Без названия")[:40]
        buttons.append([
            InlineKeyboardButton(
                text=f"📄 {i}. {title}...",
                callback_data=f"article_{article.get('id', i)}"
            )
        ])
    
    # Navigation
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{page-1}"))
    if len(articles) > (page + 1) * 5:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Actions
    buttons.append([
        InlineKeyboardButton(text="📋 Выбрать все", callback_data="select_all"),
        InlineKeyboardButton(text="📝 В библиографию", callback_data="to_bibliography")
    ])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def export_keyboard() -> InlineKeyboardMarkup:
    """Export format selection keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 ГОСТ", callback_data="export_gost"),
            InlineKeyboardButton(text="📑 BibTeX", callback_data="export_bibtex")
        ],
        [
            InlineKeyboardButton(text="📋 RIS", callback_data="export_ris"),
            InlineKeyboardButton(text="📝 Word", callback_data="export_docx")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])


# --- Handlers ---

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command."""
    await state.clear()
    
    welcome_text = """
🎓 **Добро пожаловать в LitFinder!**

Я помогу вам найти научные статьи и оформить список литературы по ГОСТ.

**Что я умею:**
• 🔍 Поиск по OpenAlex + CyberLeninka
• 📚 Форматирование по ГОСТ Р 7.0.100-2018
• 📤 Экспорт в Word, BibTeX, RIS

Отправьте мне поисковый запрос или нажмите кнопку ниже:
"""
    
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    """Handle /search command."""
    await state.set_state(SearchStates.waiting_query)
    await message.answer(
        "🔍 Введите поисковый запрос:\n\n"
        "Например: *machine learning in education*",
        parse_mode="Markdown"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    help_text = """
📖 **Справка по LitFinder**

**Команды:**
/start - Начать работу
/search - Поиск статей
/lists - Мои списки литературы
/settings - Настройки

**Как искать:**
1. Отправьте поисковый запрос
2. Выберите нужные статьи
3. Нажмите "В библиографию"
4. Выберите формат экспорта

**Поддерживаемые форматы:**
• ГОСТ Р 7.0.100-2018
• BibTeX (для LaTeX)
• RIS (Zotero, Mendeley)
• Word (.docx)
"""
    await message.answer(help_text, parse_mode="Markdown")


@router.message(SearchStates.waiting_query)
async def process_search_query(message: Message, state: FSMContext):
    """Process search query."""
    query = message.text.strip()
    
    if len(query) < 3:
        await message.answer("❌ Запрос слишком короткий. Минимум 3 символа.")
        return
    
    # Show loading
    loading_msg = await message.answer("🔄 Ищу статьи...")
    
    try:
        # Call API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/search",
                json={"query": query, "limit": 10}
            )
            response.raise_for_status()
            data = response.json()
        
        results = data.get("results", [])
        total = data.get("total", 0)
        
        if not results:
            await loading_msg.edit_text(
                f"😔 По запросу «{query}» ничего не найдено.\n\n"
                "Попробуйте изменить запрос.",
                reply_markup=main_menu_keyboard()
            )
            await state.clear()
            return
        
        # Store results in state
        await state.update_data(
            query=query,
            results=results,
            total=total,
            selected=[],
            page=0
        )
        await state.set_state(SearchStates.viewing_results)
        
        # Format results message
        results_text = f"📚 **Найдено: {total:,}** статей по запросу «{query}»\n\n"
        
        for i, article in enumerate(results[:5], 1):
            title = article.get("title", "Без названия")[:60]
            year = article.get("year", "—")
            citations = article.get("cited_by_count", 0)
            results_text += f"**{i}.** {title}...\n   📅 {year} | 📊 {citations} цит.\n\n"
        
        await loading_msg.edit_text(
            results_text,
            parse_mode="Markdown",
            reply_markup=search_results_keyboard(results, 0)
        )
        
    except httpx.HTTPError as e:
        logger.error(f"API error: {e}")
        await loading_msg.edit_text(
            "❌ Ошибка при поиске. Попробуйте позже.",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()


@router.callback_query(F.data == "search")
async def callback_search(callback: CallbackQuery, state: FSMContext):
    """Handle search button."""
    await state.set_state(SearchStates.waiting_query)
    await callback.message.edit_text(
        "🔍 Введите поисковый запрос:\n\n"
        "Например: *machine learning in education*",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Return to main menu."""
    await state.clear()
    await callback.message.edit_text(
        "🏠 Главное меню",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("article_"))
async def callback_article_details(callback: CallbackQuery, state: FSMContext):
    """Show article details."""
    data = await state.get_data()
    results = data.get("results", [])
    
    article_id = callback.data.replace("article_", "")
    
    # Find article
    article = next((a for a in results if str(a.get("id")) == article_id), None)
    
    if not article:
        await callback.answer("Статья не найдена")
        return
    
    # Format details
    title = article.get("title", "Без названия")
    year = article.get("year", "—")
    authors = article.get("authors", [])
    author_names = ", ".join(a.get("name", "") for a in authors[:3])
    if len(authors) > 3:
        author_names += " и др."
    
    abstract = article.get("abstract", "")[:500]
    if len(article.get("abstract", "")) > 500:
        abstract += "..."
    
    doi = article.get("doi", "")
    citations = article.get("cited_by_count", 0)
    
    details = f"""
📄 **{title}**

👤 {author_names or "Авторы не указаны"}
📅 {year}
📊 Цитирований: {citations}
"""
    
    if doi:
        details += f"\n🔗 DOI: {doi}"
    
    if abstract:
        details += f"\n\n📝 **Аннотация:**\n{abstract}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить в список", callback_data=f"add_{article_id}"),
            InlineKeyboardButton(text="🔗 Открыть", url=f"https://doi.org/{doi}" if doi else "https://openalex.org")
        ],
        [InlineKeyboardButton(text="🔙 К результатам", callback_data="back_to_results")]
    ])
    
    await callback.message.edit_text(details, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "back_to_results")
async def callback_back_to_results(callback: CallbackQuery, state: FSMContext):
    """Return to search results."""
    data = await state.get_data()
    results = data.get("results", [])
    query = data.get("query", "")
    total = data.get("total", 0)
    page = data.get("page", 0)
    
    results_text = f"📚 **Найдено: {total:,}** статей по запросу «{query}»\n\n"
    
    for i, article in enumerate(results[page*5:(page+1)*5], 1):
        title = article.get("title", "Без названия")[:60]
        year = article.get("year", "—")
        citations = article.get("cited_by_count", 0)
        results_text += f"**{i}.** {title}...\n   📅 {year} | 📊 {citations} цит.\n\n"
    
    await callback.message.edit_text(
        results_text,
        parse_mode="Markdown",
        reply_markup=search_results_keyboard(results, page)
    )
    await callback.answer()


@router.callback_query(F.data == "to_bibliography")
async def callback_to_bibliography(callback: CallbackQuery, state: FSMContext):
    """Generate bibliography from selected articles."""
    data = await state.get_data()
    results = data.get("results", [])
    selected = data.get("selected", [])
    
    # If nothing selected, use all displayed
    articles = [r for r in results if r.get("id") in selected] if selected else results[:5]
    
    if not articles:
        await callback.answer("Выберите хотя бы одну статью")
        return
    
    await callback.message.edit_text(
        f"📝 Выбрано {len(articles)} статей\n\n"
        "Выберите формат экспорта:",
        reply_markup=export_keyboard()
    )
    await state.update_data(articles_for_export=articles)
    await callback.answer()


@router.callback_query(F.data.startswith("export_"))
async def callback_export(callback: CallbackQuery, state: FSMContext):
    """Export bibliography."""
    format_type = callback.data.replace("export_", "")
    data = await state.get_data()
    articles = data.get("articles_for_export", [])
    
    if not articles:
        await callback.answer("Нет статей для экспорта")
        return
    
    loading_msg = await callback.message.edit_text("📤 Генерирую библиографию...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/bibliography",
                json={"articles": articles}
            )
            response.raise_for_status()
            result = response.json()
        
        # Send formatted bibliography
        if format_type == "gost":
            text = "\n".join(result.get("formatted_list", []))
            await loading_msg.edit_text(
                f"📚 **Список литературы (ГОСТ):**\n\n{text}",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        elif format_type == "bibtex":
            bibtex = result.get("bibtex", "")
            await loading_msg.edit_text(
                f"📑 **BibTeX:**\n\n```\n{bibtex[:3000]}\n```",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        elif format_type == "ris":
            ris = result.get("ris", "")
            await loading_msg.edit_text(
                f"📋 **RIS:**\n\n```\n{ris[:3000]}\n```",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            await loading_msg.edit_text(
                "📝 Формат Word будет доступен в следующей версии.",
                reply_markup=main_menu_keyboard()
            )
        
    except httpx.HTTPError as e:
        logger.error(f"Export error: {e}")
        await loading_msg.edit_text(
            "❌ Ошибка экспорта",
            reply_markup=main_menu_keyboard()
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Show help."""
    await cmd_help(callback.message)
    await callback.answer()


# --- Main ---

async def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    logger.info("🤖 LitFinder Bot starting...")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
