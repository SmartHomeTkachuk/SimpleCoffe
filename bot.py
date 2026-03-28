import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
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
            "espresso": {"id": "espresso", "name": "Эспрессо", "price": 120, "desc": "Классический эспрессо 30 мл"},
            "latte": {"id": "latte", "name": "Латте", "price": 220, "desc": "Нежный латте с пышной пенкой"},
            "cappuccino": {"id": "cappuccino", "name": "Капучино", "price": 210, "desc": "Сбалансированный капучино"},
            "americano": {"id": "americano", "name": "Американо", "price": 150, "desc": "Американо с добавлением воды"}
        }
    },
    "desserts": {
        "name": "🍰 Десерты",
        "items": {
            "cheesecake": {"id": "cheesecake", "name": "Чизкейк", "price": 280, "desc": "Нью-Йорк чизкейк с ягодным соусом"},
            "brownie": {"id": "brownie", "name": "Брауни", "price": 200, "desc": "Шоколадное брауни с грецким орехом"},
            "croissant": {"id": "croissant", "name": "Круассан", "price": 150, "desc": "Свежий круассан с маслом"}
        }
    },
    "sandwiches": {
        "name": "🥪 Сэндвичи",
        "items": {
            "chicken": {"id": "chicken", "name": "С курицей", "price": 320, "desc": "Цыпленок гриль, салат, томат, соус цезарь"},
            "salmon": {"id": "salmon", "name": "С лососем", "price": 380, "desc": "Слабосоленый лосось, сливочный сыр, шпинат"}
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
    current = State()  # храним индекс текущего вопроса и баллы

class Order(StatesGroup):
    cart = State()           # просмотр корзины
    address = State()        # адрес доставки
    delivery_time = State()  # время доставки
    comment = State()        # комментарий
    payment_method = State() # способ оплаты

# --- ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ (в памяти) ---
users: Dict[int, Dict] = {}  # user_id -> {bonuses, cart, orders}
orders: List[Dict] = []      # список заказов для демонстрации истории

def get_user(user_id: int) -> Dict:
    if user_id not in users:
        users[user_id] = {
            "bonuses": 0,           # бонусный баланс
            "cart": {},             # {item_id: quantity}
            "orders": []            # список id заказов (ссылки на orders)
        }
    return users[user_id]

def calculate_bonus(amount: int) -> int:
    """5% от суммы заказа"""
    return int(amount * 0.05)

# --- КЛАВИАТУРЫ ---
def main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Меню", callback_data="menu_categories")
    builder.button(text="🎁 Акции", callback_data="promotions")
    builder.button(text="🛒 Корзина", callback_data="show_cart")
    builder.button(text="👤 Профиль", callback_data="profile")
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
    for item_id, item in menu_data[category_key]["items"].items():
        builder.button(text=f"{item['name']} - {item['price']}₽", callback_data=f"item_{category_key}_{item_id}")
    builder.button(text="🔙 Назад", callback_data="menu_categories")
    builder.adjust(1)
    return builder.as_markup()

def back_to_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    return builder.as_markup()

def cart_keyboard(user_id: int):
    """Клавиатура для корзины: кнопки +/-, удалить, оформить"""
    builder = InlineKeyboardBuilder()
    cart = get_user(user_id)["cart"]
    for item_id, qty in cart.items():
        # Ищем название товара (проходим по меню)
        name = None
        for cat in menu_data.values():
            if item_id in cat["items"]:
                name = cat["items"][item_id]["name"]
                break
        if name:
            builder.button(text=f"{name} (x{qty})", callback_data=f"cart_item_{item_id}")
            builder.button(text="➕", callback_data=f"cart_inc_{item_id}")
            builder.button(text="➖", callback_data=f"cart_dec_{item_id}")
            builder.button(text="❌", callback_data=f"cart_del_{item_id}")
            builder.adjust(1, 3)
    builder.button(text="✅ Оформить заказ", callback_data="order_start")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def order_payment_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить картой", callback_data="payment_card")
    builder.button(text="🎁 Оплатить бонусами + карта", callback_data="payment_bonus")
    return builder.as_markup()

def quiz_keyboard(question_index):
    builder = InlineKeyboardBuilder()
    options = quiz_questions[question_index]["options"]
    for i, opt in enumerate(options):
        builder.button(text=opt, callback_data=f"quiz_ans_{question_index}_{i}")
    builder.adjust(2)
    return builder.as_markup()

# --- ОБРАБОТЧИКИ ---
router = Router()

# ----- СТАРТ И ГЛАВНОЕ МЕНЮ -----
@router.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
    "☕ *Добро пожаловать в кофейню CoffeeBot!*\n"
    "_Бот создан в рамках портфолио._\n\n"
    "✨ *Что умеет:*\n"
    "📖 Меню и цены\n"
    "🛒 Корзина + доставка\n"
    "🎁 Бонусы за заказы\n"
    "⚡️ Акции\n"
    "📅 Бронирование столика\n"
    "🧠 Квиз о кофе\n"
    "📞 Контакты\n\n"
    "👇 *Выберите действие:*"
)
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "Главное меню. Выберите действие:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

# ----- МЕНЮ И КОРЗИНА -----
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
    await callback.message.edit_text(
        f"{menu_data[category_key]['name']}:\nВыберите позицию:",
        reply_markup=items_keyboard(category_key)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("item_"))
async def show_item_detail(callback: CallbackQuery):
    _, category_key, item_id = callback.data.split("_")
    item = menu_data[category_key]["items"][item_id]
    text = (
        f"*{item['name']}*\n"
        f"💰 Цена: {item['price']}₽\n"
        f"📝 {item['desc']}\n"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Добавить в корзину", callback_data=f"add_to_cart_{category_key}_{item_id}")
    builder.button(text="🔙 Назад", callback_data=f"category_{category_key}")
    builder.adjust(1)
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery):
    _, _, category_key, item_id = callback.data.split("_", 3)
    user = get_user(callback.from_user.id)
    cart = user["cart"]
    cart[item_id] = cart.get(item_id, 0) + 1
    await callback.answer(f"✅ {menu_data[category_key]['items'][item_id]['name']} добавлен в корзину!", show_alert=False)
    # Возвращаемся к деталям товара (чтобы можно было добавить ещё)
    await show_item_detail(callback)

@router.callback_query(F.data == "show_cart")
async def show_cart(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    cart = user["cart"]
    if not cart:
        await callback.answer("🛒 Ваша корзина пуста", show_alert=True)
        return
    text = "*🛒 Ваша корзина:*\n\n"
    total = 0
    for item_id, qty in cart.items():
        # Найти товар
        for cat in menu_data.values():
            if item_id in cat["items"]:
                item = cat["items"][item_id]
                subtotal = item["price"] * qty
                total += subtotal
                text += f"{item['name']} x{qty} = {subtotal}₽\n"
                break
    text += f"\n*Итого: {total}₽*"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=cart_keyboard(callback.from_user.id))
    await callback.answer()

@router.callback_query(F.data.startswith("cart_inc_"))
async def cart_increase(callback: CallbackQuery):
    item_id = callback.data.split("_")[2]
    user = get_user(callback.from_user.id)
    if item_id in user["cart"]:
        user["cart"][item_id] += 1
    await show_cart(callback)

@router.callback_query(F.data.startswith("cart_dec_"))
async def cart_decrease(callback: CallbackQuery):
    item_id = callback.data.split("_")[2]
    user = get_user(callback.from_user.id)
    if item_id in user["cart"]:
        if user["cart"][item_id] > 1:
            user["cart"][item_id] -= 1
        else:
            del user["cart"][item_id]
    await show_cart(callback)

@router.callback_query(F.data.startswith("cart_del_"))
async def cart_delete(callback: CallbackQuery):
    item_id = callback.data.split("_")[2]
    user = get_user(callback.from_user.id)
    if item_id in user["cart"]:
        del user["cart"][item_id]
    await show_cart(callback)

# ----- ОФОРМЛЕНИЕ ЗАКАЗА (FSM) -----
@router.callback_query(F.data == "order_start")
async def order_start(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    if not user["cart"]:
        await callback.answer("🛒 Корзина пуста", show_alert=True)
        return
    await callback.message.edit_text(
        "🚚 *Оформление заказа*\n\nВведите адрес доставки:",
        parse_mode="Markdown",
        reply_markup=None
    )
    await state.set_state(Order.address)
    await callback.answer()

@router.message(Order.address)
async def order_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("⏰ Укажите желаемое время доставки (например, 18:00-20:00):")
    await state.set_state(Order.delivery_time)

@router.message(Order.delivery_time)
async def order_time(message: Message, state: FSMContext):
    await state.update_data(delivery_time=message.text)
    await message.answer("📝 Комментарий к заказу (необязательно, можете пропустить, нажав /skip):")
    await state.set_state(Order.comment)

@router.message(Command("skip"), StateFilter(Order.comment))
async def skip_comment(message: Message, state: FSMContext):
    await state.update_data(comment="")
    await ask_payment_method(message, state)

@router.message(Order.comment)
async def order_comment(message: Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await ask_payment_method(message, state)

async def ask_payment_method(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    cart = user["cart"]
    total = 0
    for item_id, qty in cart.items():
        for cat in menu_data.values():
            if item_id in cat["items"]:
                total += cat["items"][item_id]["price"] * qty
                break
    await state.update_data(total=total)
    text = f"💳 Сумма заказа: {total}₽\nВаш бонусный баланс: {user['bonuses']}₽\n\nВыберите способ оплаты:"
    await message.answer(text, reply_markup=order_payment_keyboard())
    await state.set_state(Order.payment_method)

@router.callback_query(Order.payment_method, F.data == "payment_card")
async def payment_card(callback: CallbackQuery, state: FSMContext):
    await finalize_order(callback, state, use_bonus=False)

@router.callback_query(Order.payment_method, F.data == "payment_bonus")
async def payment_bonus(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    total = data["total"]
    user = get_user(callback.from_user.id)
    if user["bonuses"] > 0:
        # Можно списать бонусы частично, но для простоты списываем максимум до суммы заказа
        bonus_used = min(user["bonuses"], total)
        total_after_bonus = total - bonus_used
        await state.update_data(total=total_after_bonus, bonus_used=bonus_used)
        text = f"🎁 Списываем {bonus_used} бонусов. К оплате картой: {total_after_bonus}₽\n\nПодтвердите оплату:"
        # Покажем кнопку для подтверждения оплаты картой
        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Оплатить", callback_data="confirm_payment")
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await state.set_state(Order.payment_method)  # остаёмся в этом же состоянии, ожидаем confirm
    else:
        # Нет бонусов, предлагаем оплатить картой
        await callback.answer("У вас нет бонусов. Оплатите картой.", show_alert=True)
        await payment_card(callback, state)

@router.callback_query(F.data == "confirm_payment", StateFilter(Order.payment_method))
async def confirm_payment(callback: CallbackQuery, state: FSMContext):
    await finalize_order(callback, state, use_bonus=True)

async def finalize_order(callback: CallbackQuery, state: FSMContext, use_bonus: bool):
    data = await state.get_data()
    user = get_user(callback.from_user.id)
    cart = user["cart"]
    total = data.get("total_after_bonus", data["total"]) if use_bonus else data["total"]
    bonus_used = data.get("bonus_used", 0)

    # Создаём заказ
    order_id = len(orders) + 1
    order = {
        "id": order_id,
        "user_id": callback.from_user.id,
        "items": cart.copy(),
        "address": data["address"],
        "delivery_time": data["delivery_time"],
        "comment": data.get("comment", ""),
        "total": total,
        "bonus_used": bonus_used,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    orders.append(order)
    user["orders"].append(order_id)

    # Начисляем бонусы за заказ (5% от полной суммы)
    full_total = data["total"]
    earned_bonus = calculate_bonus(full_total)
    user["bonuses"] = user["bonuses"] - bonus_used + earned_bonus

    # Очищаем корзину
    user["cart"] = {}

    # Отправляем подтверждение
    text = (
        f"✅ *Заказ #{order_id} оформлен!*\n\n"
        f"Сумма к оплате: {total}₽\n"
        f"Списано бонусов: {bonus_used}₽\n"
        f"Начислено бонусов: {earned_bonus}₽\n"
        f"Ваш новый бонусный баланс: {user['bonuses']}₽\n\n"
        f"Доставка по адресу: {data['address']}\n"
        f"Время: {data['delivery_time']}\n"
        f"Комментарий: {data.get('comment', '—')}\n\n"
        "Спасибо за заказ! Скоро с вами свяжется оператор."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    await state.clear()
    await callback.answer()

# ----- ПРОФИЛЬ -----
@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    # Получим последние 3 заказа для истории
    user_orders = [o for o in orders if o["user_id"] == callback.from_user.id][-3:]
    text = (
        f"👤 *Ваш профиль*\n\n"
        f"🎁 Бонусный баланс: {user['bonuses']}₽\n"
        f"🛒 Заказов: {len(user['orders'])}\n\n"
        f"*Последние заказы:*\n"
    )
    if user_orders:
        for o in user_orders:
            text += f"#{o['id']} - {o['date']} - {o['total']}₽\n"
    else:
        text += "Пока нет заказов.\n"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    await callback.answer()

# ----- КОМАНДА /order (показать корзину) -----
@router.message(Command("order"))
async def order_command(message: Message):
    user = get_user(message.from_user.id)
    if not user["cart"]:
        await message.answer("🛒 Ваша корзина пуста. Добавьте товары через меню.")
        return
    # Эмулируем callback show_cart
    await show_cart(message)  # Нужно адаптировать, но проще вызвать show_cart для Message
    # Вместо этого лучше использовать отдельную функцию для отображения корзины без callback
    await show_cart_for_message(message)

async def show_cart_for_message(message: Message):
    user = get_user(message.from_user.id)
    cart = user["cart"]
    if not cart:
        await message.answer("🛒 Ваша корзина пуста.")
        return
    text = "*🛒 Ваша корзина:*\n\n"
    total = 0
    for item_id, qty in cart.items():
        for cat in menu_data.values():
            if item_id in cat["items"]:
                item = cat["items"][item_id]
                subtotal = item["price"] * qty
                total += subtotal
                text += f"{item['name']} x{qty} = {subtotal}₽\n"
                break
    text += f"\n*Итого: {total}₽*"
    await message.answer(text, parse_mode="Markdown", reply_markup=cart_keyboard(message.from_user.id))

# ----- АКЦИИ -----
@router.callback_query(F.data == "promotions")
async def show_promotions(callback: CallbackQuery):
    text = "*🎁 Наши акции:*\n\n" + "\n".join(promotions)
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    await callback.answer()

# ----- БРОНИРОВАНИЕ СТОЛИКА -----
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

# ----- КВИЗ (ИСПРАВЛЕН) -----
@router.callback_query(F.data == "quiz_start")
async def quiz_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(score=0, q_index=0)
    await callback.message.edit_text(
        "🧠 *Кофейный квиз!*\n\n"
        f"Вопрос 1/5: {quiz_questions[0]['question']}",
        parse_mode="Markdown",
        reply_markup=quiz_keyboard(0)
    )
    await state.set_state(Quiz.current)
    await callback.answer()

@router.callback_query(Quiz.current, F.data.startswith("quiz_ans_"))
async def quiz_answer(callback: CallbackQuery, state: FSMContext):
    _, q_idx_str, ans_idx_str = callback.data.split("_")
    q_idx = int(q_idx_str)
    ans_idx = int(ans_idx_str)
    correct_idx = quiz_questions[q_idx]["correct"]

    data = await state.get_data()
    score = data.get("score", 0)
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
    else:
        await state.update_data(score=score)
        text = (
            f"🎉 *Квиз завершён!*\n\n"
            f"Ваш результат: {score} из {len(quiz_questions)}.\n\n"
            "Спасибо за участие! Возвращайтесь в главное меню."
        )
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
        await state.clear()
    await callback.answer()

# ----- КОНТАКТЫ -----
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

# ----- ЗАПУСК -----
async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
