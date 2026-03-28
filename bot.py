import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8641989771:AAE8acCBrQ9nUKPdpjOHrVFuj8Nc-Ce8krY"
OWNER_CONTACT = "t.me/PythonBotDeveloper"

# --- ДАННЫЕ МЕНЮ ---
menu_data = {
    "coffee": {
        "name": "☕ Кофе",
        "items": {
            "espresso": {"name": "Эспрессо", "price": 120, "desc": "Классический эспрессо 30 мл"},
            "latte": {"name": "Латте", "price": 220, "desc": "Нежный латте с пышной пенкой"},
            "cappuccino": {"name": "Капучино", "price": 210, "desc": "Сбалансированный капучино"},
            "americano": {"name": "Американо", "price": 150, "desc": "Американо с добавлением воды"}
        }
    },
    "desserts": {
        "name": "🍰 Десерты",
        "items": {
            "cheesecake": {"name": "Чизкейк", "price": 280, "desc": "Нью-Йорк чизкейк с ягодным соусом"},
            "brownie": {"name": "Брауни", "price": 200, "desc": "Шоколадное брауни с грецким орехом"},
            "croissant": {"name": "Круассан", "price": 150, "desc": "Свежий круассан с маслом"}
        }
    },
    "sandwiches": {
        "name": "🥪 Сэндвичи",
        "items": {
            "chicken": {"name": "С курицей", "price": 320, "desc": "Цыпленок гриль, салат, томат, соус цезарь"},
            "salmon": {"name": "С лососем", "price": 380, "desc": "Слабосоленый лосось, сливочный сыр, шпинат"}
        }
    }
}

# --- АКЦИИ ---
promotions = [
    "☕ Второй кофе в подарок каждую среду!",
    "🍰 Чизкейк + капучино = 399₽ (вместо 500₽)",
    "🥪 Комбо-обед: сэндвич + американо = 399₽"
]

# --- ВОПРОСЫ КВИЗА ---
quiz_questions = [
    {
        "question": "Что такое робуста?",
        "options": ["Сорт кофе", "Способ обжарки", "Кофемашина", "Разновидность капучино"],
        "correct": 0
    },
    {
        "question": "В какой стране выращивают больше всего кофе?",
        "options": ["Колумбия", "Вьетнам", "Бразилия", "Эфиопия"],
        "correct": 2
    },
    {
        "question": "Какой напиток содержит больше всего кофеина?",
        "options": ["Эспрессо", "Фильтр-кофе", "Латте", "Капучино"],
        "correct": 1
    },
    {
        "question": "Что такое «крема»?",
        "options": ["Пена на эспрессо", "Сорт молока", "Взбитые сливки", "Кофейный ликер"],
        "correct": 0
    },
    {
        "question": "Какой метод заваривания считается самым старым?",
        "options": ["Френч-пресс", "Турка (джезва)", "Аэропресс", "Воронка"],
        "correct": 1
    }
]

# --- FSM СОСТОЯНИЯ ---
class Booking(StatesGroup):
    date = State()
    time = State()
    guests = State()

class Quiz(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()

# --- КЛАВИАТУРЫ ---
def main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Меню", callback_data="menu_categories")
    builder.button(text="🎁 Акции", callback_data="promotions")
    builder.button(text="📅 Бронирование столика", callback_data="booking_start")
    builder.button(text="🧠 Квиз", callback_data="quiz_start")
    builder.button(text="📞 Контакты", callback_data="contacts")
    builder.adjust(2)
    return builder.as_markup()

def categories_keyboard():
    builder = InlineKeyboardBuilder()
    for key, category in menu_data.items():
        builder.button(text=category["name"], callback_data=f"category_{key}")
    builder.button(text="🔙 Назад", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

def items_keyboard(category_key):
    builder = InlineKeyboardBuilder()
    for item_key, item in menu_data[category_key]["items"].items():
        builder.button(text=f"{item['name']} - {item['price']}₽", callback_data=f"item_{category_key}_{item_key}")
    builder.button(text="🔙 Назад", callback_data="menu_categories")
    builder.adjust(1)
    return builder.as_markup()

def back_to_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    return builder.as_markup()

def quiz_keyboard(question_index):
    builder = InlineKeyboardBuilder()
    options = quiz_questions[question_index]["options"]
    for i, opt in enumerate(options):
        builder.button(text=opt, callback_data=f"quiz_ans_{question_index}_{i}")
    builder.adjust(2)
    return builder.as_markup()

# --- ОБРАБОТЧИКИ (РОУТЕР) ---
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
        "☕ *Добро пожаловать в кофейню CoffeeBot!* ☕\n\n"
        "Этот бот создан в качестве *портфолио*.\n"
        f"Владелец: [{OWNER_CONTACT}](https://{OWNER_CONTACT})\n\n"
        "Здесь вы можете:\n"
        "✅ Посмотреть меню и цены\n"
        "✅ Узнать акции\n"
        "✅ Забронировать столик\n"
        "✅ Пройти квиз о кофе\n"
        "✅ Связаться с нами\n\n"
        "Выберите действие:"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "Главное меню. Выберите действие:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "menu_categories")
async def show_categories(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 *Наше меню:*\nВыберите категорию:",
        parse_mode="Markdown",
        reply_markup=categories_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("category_"))
async def show_items(callback: CallbackQuery):
    category_key = callback.data.split("_")[1]
    if category_key not in menu_data:
        await callback.answer("Категория не найдена")
        return
    category = menu_data[category_key]
    await callback.message.edit_text(
        f"{category['name']}:\nВыберите позицию:",
        reply_markup=items_keyboard(category_key)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("item_"))
async def show_item_detail(callback: CallbackQuery):
    _, category_key, item_key = callback.data.split("_")
    item = menu_data[category_key]["items"][item_key]
    text = (
        f"*{item['name']}*\n"
        f"💰 Цена: {item['price']}₽\n"
        f"📝 {item['desc']}\n\n"
        "Для заказа нажмите /order (в разработке) или свяжитесь с нами."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    await callback.answer()

@router.callback_query(F.data == "promotions")
async def show_promotions(callback: CallbackQuery):
    text = "*🎁 Наши акции:*\n\n" + "\n".join(promotions)
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    await callback.answer()

@router.callback_query(F.data == "booking_start")
async def booking_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📅 *Бронирование столика*\n\n"
        "Введите дату в формате *ДД.ММ.ГГГГ* (например, 01.06.2025):",
        parse_mode="Markdown",
        reply_markup=None
    )
    await state.set_state(Booking.date)
    await callback.answer()

@router.message(Booking.date)
async def booking_date(message: Message, state: FSMContext):
    if len(message.text) != 10 or message.text[2] != '.' or message.text[5] != '.':
        await message.answer("❌ Неверный формат. Попробуйте снова (ДД.ММ.ГГГГ):")
        return
    await state.update_data(date=message.text)
    await message.answer("⏰ Введите время (например, 18:00):")
    await state.set_state(Booking.time)

@router.message(Booking.time)
async def booking_time(message: Message, state: FSMContext):
    if ":" not in message.text:
        await message.answer("❌ Неверный формат. Введите время в формате ЧЧ:ММ (например, 18:00):")
        return
    await state.update_data(time=message.text)
    await message.answer("👥 Введите количество гостей (1-6):")
    await state.set_state(Booking.guests)

@router.message(Booking.guests)
async def booking_guests(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 1 or int(message.text) > 6:
        await message.answer("❌ Количество гостей должно быть числом от 1 до 6. Повторите:")
        return
    await state.update_data(guests=message.text)
    data = await state.get_data()
    text = (
        "✅ *Бронирование принято!*\n\n"
        f"📅 Дата: {data['date']}\n"
        f"⏰ Время: {data['time']}\n"
        f"👥 Гостей: {data['guests']}\n\n"
        "Мы свяжемся с вами для подтверждения.\n"
        "Вернуться в главное меню: /start"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    await state.clear()

@router.callback_query(F.data == "quiz_start")
async def quiz_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🧠 *Кофейный квиз!*\n\n"
        "Проверьте свои знания о кофе. Отвечайте на вопросы.\n\n"
        f"Вопрос 1/5: {quiz_questions[0]['question']}",
        parse_mode="Markdown",
        reply_markup=quiz_keyboard(0)
    )
    await state.set_state(Quiz.q1)
    await callback.answer()

@router.callback_query(F.data.startswith("quiz_ans_"), StateFilter(Quiz))
async def quiz_answer(callback: CallbackQuery, state: FSMContext):
    _, q_idx_str, ans_idx_str = callback.data.split("_")
    q_idx = int(q_idx_str)
    ans_idx = int(ans_idx_str)
    correct_idx = quiz_questions[q_idx]["correct"]

    user_data = await state.get_data()
    score = user_data.get("score", 0)
    if ans_idx == correct_idx:
        score += 1
        await callback.answer("✅ Правильно!")
    else:
        correct_text = quiz_questions[q_idx]["options"][correct_idx]
        await callback.answer(f"❌ Неправильно. Правильный ответ: {correct_text}", show_alert=True)

    await state.update_data(score=score)

    next_q = q_idx + 1
    if next_q < len(quiz_questions):
        await callback.message.edit_text(
            f"🧠 Вопрос {next_q+1}/{len(quiz_questions)}: {quiz_questions[next_q]['question']}",
            parse_mode="Markdown",
            reply_markup=quiz_keyboard(next_q)
        )
        if next_q == 1:
            await state.set_state(Quiz.q2)
        elif next_q == 2:
            await state.set_state(Quiz.q3)
        elif next_q == 3:
            await state.set_state(Quiz.q4)
        elif next_q == 4:
            await state.set_state(Quiz.q5)
    else:
        final_score = score + (1 if ans_idx == correct_idx else 0)
        await state.update_data(score=final_score)
        text = (
            f"🎉 *Квиз завершён!*\n\n"
            f"Ваш результат: {final_score} из {len(quiz_questions)}.\n\n"
            "Спасибо за участие! Возвращайтесь в главное меню."
        )
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
        await state.clear()

@router.callback_query(F.data == "contacts")
async def show_contacts(callback: CallbackQuery):
    text = (
        "📞 *Наши контакты:*\n\n"
        "📍 Адрес: ул. Кофейная, 10\n"
        "📱 Телефон: +7 (999) 123-45-67\n"
        "🌐 Сайт: coffee-place.ru\n"
        "✉️ Email: hello@coffee-place.ru\n\n"
        f"Владелец бота (портфолио): [{OWNER_CONTACT}](https://{OWNER_CONTACT})"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    await callback.answer()

# --- ЗАПУСК ---
async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())