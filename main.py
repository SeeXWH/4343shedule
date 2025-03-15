import asyncio

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import StateFilter
from aiogram.filters.command import Command
from dataclasses import dataclass
import json
from datetime import datetime, time, timedelta

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import BotCommand, InlineKeyboardButton
from aiogram.enums import ParseMode
import pytz
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pyexpat.errors import messages

moscow_tz = pytz.timezone("Europe/Moscow")
bot = Bot(token="8092647573:AAGnfcFZLW9znsqKQVITLzZs4xYw--efn1E")

dp = Dispatcher()


@dataclass
class WeekInfo:
    day_name: str
    is_even_week: bool


admin = [770833127, 1347201856]


class EditState:
    SELECT_WEEK = "select_week"
    SELECT_DAY = "select_day"
    SELECT_PAIR = "select_pair"
    EDIT_FIELD = "edit_field"


WEEKS = {"even": "Чётная неделя", "not_even": "Нечётная неделя"}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
PAIRS = ["1", "2", "3", "4", "5", "6"]
FIELDS = {"name": "Название", "description": "Описание", "type": "Тип", "delete" : "Удалить"}
TYPES = {"lecture": "Лекция (Л)", "practice": "Практика (Пр)", "lab": "Лабораторная (Лр)"}
user_data = {}

times = {
    "1": "9:30 - 11:00",
    "2": "11:10 - 12:40",
    "3": "13:00 - 14:30",
    "4": "15:00 - 16:30",
    "5": "16:40 - 18:10",
    "6": "18:30 - 20:00"
}

days = {
    "Monday": "Понедельник",
    "Tuesday": "Вторник",
    "Wednesday": "Среда",
    "Thursday": "Четверг",
    "Friday": "Пятница",
    "Saturday": "Суббота",
    "Sunday": "Воскресенье"

}

type_mapping = {
    "lecture": "(Л)",
    "practice": "(Пр)",
    "lab": "(Лр)"
}


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="schedule", description="Получить расписание"),
        BotCommand(command="all", description="Получить все расписание"),
        BotCommand(command="mailing", description="подписаться на рассылку"),
        BotCommand(command="cancel", description="отказаться от рассылки"),
        BotCommand(command="edit", description="редактируем расписание"),
    ]
    await bot.set_my_commands(commands)


def get_week_info() -> WeekInfo:
    url = 'https://api.guap.ru/rasp/v1/get-info'
    headers = {'accept': 'text/plain'}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Ошибка запроса: {response.status_code}")

    data = response.json()

    current_day = data['currentDay'] - 1
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = days[current_day]

    is_even_week = data['currentWeek'] % 2 == 0

    return WeekInfo(day_name=day_name, is_even_week=is_even_week)


def print_schedule(next_week: bool):
    info = get_week_info()
    current_date = datetime.now(moscow_tz)
    if next_week:
        current_date = current_date + timedelta(days=1)
    if next_week and info.day_name == "Sunday":
        if info.is_even_week:
            info.is_even_week = False
        else:
            info.is_even_week = True
    if info.is_even_week:
        with open("even.json", "r", encoding="utf-8") as file:
            schedule = json.load(file)
    else:
        with open("notEven.json", "r", encoding="utf-8") as file:
            schedule = json.load(file)
    if next_week:
        day = get_next_day(info.day_name)
    else:
        day = info.day_name
    call_day = days[day]
    if day == "Sunday":
        return "<b>" + call_day + "</b> (" + str(current_date.date().day) + "." + str(
            current_date.date().month) + ")\n" + "    Пар нет, отдыхаем 🥳"
    if day not in schedule:
        return "День недели не найден."
    day_schedule = schedule[day][0]
    formatted_schedule = [
        "<b>" + call_day + "</b> (" + str(current_date.date().day) + "." + str(current_date.date().month) + ")"]

    for key, value in day_schedule.items():
        if value["name"] and value["type"]:
            time = times[key]
            name = value["name"]
            description = value["description"]
            if description.lower() == "none":
                description = ""
            if description != "":
                description = "\n    ‼️ " + description
            type_ = type_mapping.get(value["type"], "")
            formatted_schedule.append(f"    <b>{key}</b>. {name} <b>{type_}</b>\n    <i>({time})</i>{description}")

    if len(formatted_schedule) == 1:
        formatted_schedule.append("    Пар нет, отдыхаем 🥳")

    return "\n".join(formatted_schedule) + "\n"


def format_week_schedule(schedule: dict, week_title: str):
    formatted_schedule = [f"{week_title}"]

    for day, pairs in schedule.items():
        call_day = days[day]
        formatted_schedule.append(f"\n<b>{call_day}</b>   ")
        day_schedule = pairs[0]

        has_pairs = False

        for pair_number, pair_info in day_schedule.items():
            if pair_info["name"] and pair_info["type"]:
                time = times[pair_number]
                name = pair_info["name"]
                description = pair_info["description"]
                if description.lower() == "none":
                    description = ""
                if description != "":
                    description = "\n    ‼️ " + description

                type_ = type_mapping.get(pair_info["type"], "")
                formatted_schedule.append(f"    <b>{pair_number}</b>. {name} <b>{type_}</b>\n    <i>({time})</i>{description}")
                has_pairs = True

        if not has_pairs:
            formatted_schedule.append("    Пар нет, отдыхаем 🥳")

    return "\n".join(formatted_schedule)


def print_even_week_schedule():
    with open("even.json", "r", encoding="utf-8") as file:
        even_schedule = json.load(file)
    return format_week_schedule(even_schedule, "🔵Чётная неделя")


def print_not_even_week_schedule():
    with open("notEven.json", "r", encoding="utf-8") as file:
        not_even_schedule = json.load(file)
    return format_week_schedule(not_even_schedule, "🔴Нечётная неделя")


def load_schedule(filename: str):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_schedule(filename: str, schedule: dict):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(schedule, file, ensure_ascii=False, indent=2)


def save_user_id(user_id: int):
    user_ids = load_ids("users.txt")
    if user_id not in user_ids:
        with open("users.txt", "a") as file:
            file.write(f"{user_id}\n")


def save_chat_id(chat_id: int):
    chat_ids = load_ids("chats.txt")
    if chat_id not in chat_ids:
        with open("chats.txt", "a") as file:
            file.write(f"{chat_id}\n")


def remove_user_id(user_id: int):
    user_ids = load_ids("users.txt")
    if user_id in user_ids:
        user_ids.remove(user_id)
        with open("users.txt", "w") as file:
            for id_ in user_ids:
                file.write(f"{id_}\n")


def remove_chat_id(chat_id: int):
    chat_ids = load_ids("chats.txt")
    if chat_id in chat_ids:
        chat_ids.remove(chat_id)
        with open("chats.txt", "w") as file:
            for id_ in chat_ids:
                file.write(f"{id_}\n")


def load_ids(filename: str):
    try:
        with open(filename, "r") as file:
            return [int(line.strip()) for line in file.readlines()]
    except FileNotFoundError:
        return []


def get_next_day(current_day: str) -> str:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current_index = days.index(current_day)
    next_index = (current_index + 1) % len(days)
    return days[next_index]


async def send_current_scheduled_messages():
    while True:
        now = datetime.now(moscow_tz).time()
        target_time = time(11, 40)

        if now.hour == target_time.hour and now.minute == target_time.minute:
            user_ids = load_ids("users.txt")
            for user_id in user_ids:
                try:
                    await bot.send_message(user_id, "Расписание на сегодня: \n" + print_schedule(False),
                                           parse_mode=ParseMode.HTML)
                    await bot.send_message(user_id, print_schedule("Расписание на завтра: \n" + print_schedule(True)),
                                           parse_mode=ParseMode.HTML)
                except Exception as e:
                    print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

            chat_ids = load_ids("chats.txt")
            for chat_id in chat_ids:
                try:
                    await bot.send_message(chat_id, print_schedule("Расписание на сегодня: \n" + print_schedule(False)),
                                           parse_mode=ParseMode.HTML)
                    await bot.send_message(chat_id, print_schedule("Расписание на завтра: \n" + print_schedule(True)),
                                           parse_mode=ParseMode.HTML)
                except Exception as e:
                    print(f"Не удалось отправить сообщение в чат {chat_id}: {e}")

        await asyncio.sleep(60)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Я присылаю расписание каждый день")


@dp.message(Command("mailing"))
async def cmd_mailing(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type in ["group", "supergroup", "channel"]:
        save_chat_id(chat_id)
    user_id = message.from_user.id
    save_user_id(user_id)
    await message.answer("Теперь каждый день сюда буду присылать расписание!")


@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type in ["group", "supergroup", "channel"]:
        remove_chat_id(chat_id)
    user_id = message.from_user.id
    remove_user_id(user_id)
    await message.answer("Отменил рассылку!")


@dp.message(Command("schedule"))
async def cmd_schedule(message: types.Message):
    await message.answer("Расписание на сегодня: \n" + print_schedule(False), parse_mode=ParseMode.HTML)
    await message.answer("Расписание на завтра: \n" + print_schedule(True), parse_mode=ParseMode.HTML)


@dp.message(Command("all"))
async def all_schedule(message: types.Message):
    if get_week_info().is_even_week:
        await message.answer(print_even_week_schedule(), parse_mode=ParseMode.HTML)
        await message.answer(print_not_even_week_schedule(), parse_mode=ParseMode.HTML)
    else:
        await message.answer(print_not_even_week_schedule(), parse_mode=ParseMode.HTML)
        await message.answer(print_even_week_schedule(), parse_mode=ParseMode.HTML)


@dp.message(Command("edit"))
async def cmd_edit(message: types.Message):
    user_id = message.from_user.id
    if message.chat.type in ["group", "supergroup", "channel"]:
        await message.answer("Нельзя в группе☠️")
    elif user_id not in admin:
        await message.answer("Нет доступа❌")
    elif user_id in admin:
        builder = InlineKeyboardBuilder()
        for week, label in WEEKS.items():
            builder.add(InlineKeyboardButton(text=label, callback_data=f"week:{week}"))
        builder.add(InlineKeyboardButton(text="Назад", callback_data="back"))
        builder.adjust(1)
        if get_week_info().is_even_week:
            await message.answer(print_even_week_schedule(), parse_mode=ParseMode.HTML)
            await message.answer(print_not_even_week_schedule(), parse_mode=ParseMode.HTML)
        else:
            await message.answer(print_not_even_week_schedule(), parse_mode=ParseMode.HTML)
            await message.answer(print_even_week_schedule(), parse_mode=ParseMode.HTML)
        await message.answer("Выберите неделю:", reply_markup=builder.as_markup())


# Обработка выбора недели
@dp.callback_query(lambda c: c.data.startswith("week:"))
async def process_week(callback: types.CallbackQuery):
    week = callback.data.split(":")[1]
    user_data[callback.from_user.id] = {"week": week}
    builder = InlineKeyboardBuilder()
    for day in DAYS:
        builder.add(InlineKeyboardButton(text=day, callback_data=f"day:{day}"))
    builder.add(InlineKeyboardButton(text="Назад", callback_data="back"))
    builder.adjust(2)
    await callback.message.edit_text("Выберите день недели:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("day:"))
async def process_day(callback: types.CallbackQuery):
    day = callback.data.split(":")[1]
    user_data[callback.from_user.id]["day"] = day
    builder = InlineKeyboardBuilder()
    for pair in PAIRS:
        builder.add(InlineKeyboardButton(text=pair, callback_data=f"pair:{pair}"))
    builder.add(InlineKeyboardButton(text="Назад", callback_data="back"))
    builder.adjust(3)
    await callback.message.edit_text("Выберите номер пары:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("pair:"))
async def process_pair(callback: types.CallbackQuery):
    pair = callback.data.split(":")[1]
    user_data[callback.from_user.id]["pair"] = pair
    builder = InlineKeyboardBuilder()
    for field, label in FIELDS.items():
        builder.add(InlineKeyboardButton(text=label, callback_data=f"field:{field}"))
    builder.add(InlineKeyboardButton(text="Назад", callback_data="back"))
    builder.adjust(1)
    await callback.message.edit_text("Выберите поле для редактирования:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("field:"))
async def process_field(callback: types.CallbackQuery):
    field = callback.data.split(":")[1]
    user_data[callback.from_user.id]["field"] = field

    if field == "type":
        builder = InlineKeyboardBuilder()
        for type_key, type_label in TYPES.items():
            builder.add(InlineKeyboardButton(text=type_label, callback_data=f"type:{type_key}"))
        builder.add(InlineKeyboardButton(text="Назад", callback_data="back"))
        builder.adjust(1)
        await callback.message.edit_text("Выберите тип пары:", reply_markup=builder.as_markup())
    elif field == "delete":
        user_id = callback.from_user.id
        week = user_data[user_id]["week"]
        day = user_data[user_id]["day"]
        pair = user_data[user_id]["pair"]

        filename = "even.json" if week == "even" else "notEven.json"
        schedule = load_schedule(filename)
        schedule[day][0][pair]["name"] = ""
        schedule[day][0][pair]["description"] = ""
        schedule[day][0][pair]["type"] = ""
        await callback.message.edit_text(f"Пара №{pair} в {day} удалена")
        save_schedule(filename, schedule)
        del user_data[user_id]
    else:
        await callback.message.edit_text(f"Введите новое значение для поля '{FIELDS[field]}':")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("type:"))
async def process_type(callback: types.CallbackQuery):
    type_key = callback.data.split(":")[1]
    user_id = callback.from_user.id
    week = user_data[user_id]["week"]
    day = user_data[user_id]["day"]
    pair = user_data[user_id]["pair"]

    filename = "even.json" if week == "even" else "notEven.json"
    schedule = load_schedule(filename)

    if day in schedule and pair in schedule[day][0]:
        schedule[day][0][pair]["type"] = type_key
        save_schedule(filename, schedule)
        await callback.message.edit_text(f"Тип пары {pair} в день {day} изменён на: {TYPES[type_key]}")
    else:
        await callback.message.edit_text("Ошибка: день или пара не найдены.")

    del user_data[user_id]

@dp.message()
async def process_text(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_data:
        week = user_data[user_id]["week"]
        day = user_data[user_id]["day"]
        pair = user_data[user_id]["pair"]
        field = user_data[user_id]["field"]
        new_value = message.text

        filename = "even.json" if week == "even" else "notEven.json"
        schedule = load_schedule(filename)

        if day in schedule and pair in schedule[day][0]:
            schedule[day][0][pair][field] = new_value
            save_schedule(filename, schedule)
            await message.answer(f"Поле '{FIELDS[field]}' для пары {pair} в день {day} изменено на: {new_value}")
        else:
            await message.answer("Ошибка: день или пара не найдены.")

        del user_data[user_id]

@dp.callback_query(lambda c: c.data == "back")
async def process_back(callback: types.CallbackQuery):
    await callback.message.edit_text("Возврат в главное меню.")



@dp.message()
async def handle_messages(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type in ["group", "supergroup", "channel"]:
        save_chat_id(chat_id)


async def main():
    asyncio.create_task(send_current_scheduled_messages())
    await set_bot_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("Starting...")
    asyncio.run(main())
