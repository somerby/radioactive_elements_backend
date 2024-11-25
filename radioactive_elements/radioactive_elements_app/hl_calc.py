import re
import math

class HalfLifeCalculation:
    UNIT_CONVERSIONS = {
        'т': 1000000,
        'тонна': 1000000,
        'тонны': 1000000,
        'тонн': 1000000,
        'кг': 1000,
        'килограмм': 1000,
        'килограммов': 1000,
        'г': 1,
        'грамм': 1,
        'граммов': 1,
        'мг': 0.001,
        'миллиграмм': 0.001,
        'миллиграммов': 0.001,
        'мкг': 0.000001,
        'микрограмм': 0.000001,
        'микрограммов': 0.000001,
        'мкс': 0.000001,
        'микросекунд': 0.000001,
        'микросекунда': 0.000001,
        'мс': 0.000001,
        'миллисекунд': 0.000001,
        'миллисекунда': 0.000001,
        'с': 0.000001,
        'секунд': 0.000001,
        'секунда': 0.000001,
        'м': 60,
        'минут': 60,
        'минута': 60,
        'ч': 3600,
        'час': 3600,
        'часа': 3600,
        'часов': 3600,
        'д': 86400,
        'день': 86400,
        'дней': 86400,
        'дня': 86400,
        'н': 604800,
        'неделя': 604800,
        'недели': 604800,
        'недель': 604800,
        'мес': 2678400,
        'месяц': 2678400,
        'месяца': 2678400,
        'месяцев': 2678400,
        'г': 31536000,
        'год': 31536000,
        'года': 31536000,
        'лет': 31536000,
        'л': 31536000,
    }

    MASS_UNIT_CONVERSIONS = {
        1000000: 'т',
        1000: 'кг',
        1: 'г',
        0.001: 'мг',
        0.000001: 'мкг',
    }

    @classmethod
    def unit_parse(cls, text):
        match = re.match(r'(\d+[.,]?\d*)\s*(\D+)', text)
        if not match:
            raise NameError()
        value = float(match.group(1).replace(',', '.'))
        unit = match.group(2).strip().lower()
        if unit in cls.UNIT_CONVERSIONS:
            return value * cls.UNIT_CONVERSIONS[unit]
        else:
            raise ValueError()

    @classmethod
    def half_life_calculation(cls, pass_time_text, quantity_text, period_time):
        pass_time = cls.unit_parse(pass_time_text)
        quantity = cls.unit_parse(quantity_text)
        lambda_decay = math.log(2) / period_time
        remaining_mass = quantity * math.exp(-lambda_decay * pass_time)
        for unit_mass in cls.MASS_UNIT_CONVERSIONS:
            if remaining_mass > unit_mass:
                return str(remaining_mass / unit_mass) + ' ' + cls.MASS_UNIT_CONVERSIONS[unit_mass]
        return (str(remaining_mass) + ' г')[:39]