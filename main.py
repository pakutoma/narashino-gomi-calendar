import calendar
import os
import pathlib
import shutil
from datetime import datetime

import arrow
import numpy as np
from PIL import Image
from ics import Calendar, Event
from pdf2image import convert_from_path

import constants as con
import settings


def main():
    calendars = pdf_to_bmp()
    for cal in calendars:
        months = split_calendar(cal)
        days = []
        for month in months:
            days += get_garbage_days_in_month(month)
        ical = build_ical(days)
        name = os.path.basename(cal)[:-4] + '.ics'
        with open(f'icals/{name}', 'w') as f:
            f.write(ical)


def build_ical(days: [(datetime, str)]) -> str:
    cal = Calendar()
    cal.creator = con.AUTHOR
    for day in days:
        dt, garbage_type = day
        arrow_dt = arrow.get(dt)
        event = Event(name=con.WORDS[garbage_type], begin=arrow_dt, end=arrow_dt)
        event.make_all_day()
        cal.events.add(event)
    return str(cal)


def get_garbage_days_in_month(month_image_path: str) -> [(datetime, str)]:
    day_images = crop_day(month_image_path)
    month_index = int(os.path.basename(month_image_path)[0:2].strip('_'))
    start, end = calc_month_range(month_index)
    garbage_days = []
    for day_index, day_image in enumerate(day_images[start:end]):
        garbage_type = get_garbage_type(day_image[1])
        if garbage_type != 'none':
            garbage_days.append((get_datetime(month_index, day_index), garbage_type))
    return garbage_days


def get_datetime(month_index: int, day_index: int):
    month = 12 if (month_index + 4) % 12 == 0 else (month_index + 4) % 12
    year = settings.YEAR if month > 3 else settings.YEAR + 1
    day = day_index + 1
    return datetime(year, month, day, hour=8)


def get_garbage_type(day_image: Image) -> str:
    color = find_mode_color(day_image)
    return get_garbage_type_by_color(color)


def get_garbage_type_by_color(color: (int, int, int)) -> str:
    return list(con.CALENDAR_COLORS.keys())[np.argmin([distance(color, cc) for cc in con.CALENDAR_COLORS.values()])]


def distance(color1: (int, int, int), color2: (int, int, int)) -> float:
    r_diff = float(color1[0]) - float(color2[0])
    g_diff = float(color1[1]) - float(color2[1])
    b_diff = float(color1[2]) - float(color2[2])
    return (r_diff**2 + g_diff**2 + b_diff**2)**0.5


def find_mode_color(image: Image) -> (int, int, int):
    img_array = np.array(image)
    img_array = img_array.reshape((-1, 3))
    values, counts = np.unique(img_array, axis=0, return_counts=True)
    colors = [(counts[i], tuple(color)) for i, color in enumerate(values) if tuple(color) not in con.IGNORE_COLORS]
    colors.sort(key=lambda x: x[0], reverse=True)
    return colors[0][1]


def calc_month_range(month_index: int) -> (int, int):
    month = 12 if (month_index + 4) % 12 == 0 else (month_index + 4) % 12
    year = settings.YEAR if month > 3 else settings.YEAR + 1
    start, num = calendar.monthrange(year, month)
    start = (start + 1) % 7
    end = start + num
    return start, end


def pdf_to_bmp() -> [str]:
    work_dir = 'work/orig'
    try:
        shutil.rmtree(work_dir)
    except FileNotFoundError:
        pass
    os.mkdir(work_dir)
    pdfs = pathlib.Path('pdfs').glob('**/*.pdf')
    calendar_images = [(pdf.name, convert_from_path(pdf, poppler_path=settings.POPPLER_PATH)[0]) for pdf in pdfs]
    for calendar_image in calendar_images:
        name = calendar_image[0][:-4]
        calendar_image[1].save(f'{work_dir}/{name}.bmp')
    return [f'{work_dir}/{calendar_image[0][:-4]}.bmp' for calendar_image in calendar_images]


def split_calendar(orig_path: str) -> [str]:
    work_dir = 'work/month'
    try:
        shutil.rmtree(work_dir)
    except FileNotFoundError:
        pass
    os.mkdir(work_dir)
    months = crop_month(orig_path)
    month_paths = []
    for month in months:
        name, image = month
        image.save(f'{work_dir}/{name}')
        month_paths.append(f'{work_dir}/{name}')
    return month_paths


def crop_month(orig_path: str) -> [(str, Image)]:
    return crop_calendar(orig_path,
                         con.MONTH_X_START, con.MONTH_Y_START, con.MONTH_X_LEN, con.MONTH_Y_LEN, con.MONTH_X_NUM,
                         con.MONTH_Y_NUM)


def crop_day(month_path: str) -> [(str, Image)]:
    return crop_calendar(month_path,
                         con.DAY_X_START, con.DAY_Y_START, con.DAY_X_LEN, con.DAY_Y_LEN, con.DAY_X_NUM, con.DAY_Y_NUM)


def crop_calendar(image_path: str,
                  x_start: int, y_start: int, x_len: int, y_len: int, x_num: int, y_num: int) -> [(str, Image)]:
    calendar_image = Image.open(image_path)
    cropped_images: [(str, Image)] = []
    for c in range(0, y_num):
        for r in range(0, x_num):
            x = x_start + x_len * r
            y = y_start + y_len * c
            cropped_image = calendar_image.crop((x, y, x + x_len, y + y_len))
            index = c * x_num + r
            name = os.path.basename(image_path)
            cropped_images.append((f'{index}_{name}', cropped_image))
    return cropped_images


if __name__ == '__main__':
    main()
