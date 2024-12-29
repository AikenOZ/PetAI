import sys
import tkinter as tk
import random
import time
import math
from PIL import Image, ImageDraw, ImageTk
import pystray
from dataclasses import dataclass
from typing import Tuple, Optional
import json
import os
from datetime import datetime, timedelta

@dataclass
class CatState:
    """Класс для хранения состояния кота"""
    energy: float = 100.0
    happiness: float = 100.0
    hunger: float = 0.0
    last_update: float = time.time()
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    state_change_time: float = time.time()

class CatPersonality:
    """Класс для определения личности кота"""
    def __init__(self):
        self.playfulness = random.uniform(0.3, 1.0)
        self.laziness = random.uniform(0.3, 1.0)
        self.curiosity = random.uniform(0.3, 1.0)
        self.friendliness = random.uniform(0.3, 1.0)
        
        # Сохраняем личность кота
        self.save_personality()
    
    def save_personality(self):
        """Сохранение личности кота в файл"""
        data = {
            "playfulness": self.playfulness,
            "laziness": self.laziness,
            "curiosity": self.curiosity,
            "friendliness": self.friendliness
        }
        try:
            with open('cat_personality.json', 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Не удалось сохранить личность кота: {e}")

    @classmethod
    def load_personality(cls):
        """Загрузка личности кота из файла"""
        try:
            with open('cat_personality.json', 'r') as f:
                data = json.load(f)
                personality = cls()
                personality.playfulness = data["playfulness"]
                personality.laziness = data["laziness"]
                personality.curiosity = data["curiosity"]
                personality.friendliness = data["friendliness"]
                return personality
        except:
            return cls()

class CatAI:
    """Искусственный интеллект кота"""
    def __init__(self):
        self.state = CatState()
        self.personality = CatPersonality.load_personality()
        self.current_behavior = 'idle'
        self.behaviors = {
            'idle': {'weight': 1.0, 'duration': (3, 8)},
            'walking': {'weight': 0.7, 'duration': (5, 15)},
            'playing': {'weight': 0.5, 'duration': (5, 10)},
            'sleeping': {'weight': 0.3, 'duration': (10, 30)},
            'hunting': {'weight': 0.4, 'duration': (3, 8)}
        }
        
        # Загружаем предыдущее состояние, если есть
        self.load_state()

    def save_state(self):
        """Сохранение состояния кота"""
        data = {
            "energy": self.state.energy,
            "happiness": self.state.happiness,
            "hunger": self.state.hunger,
            "last_update": self.state.last_update
        }
        try:
            with open('cat_state.json', 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Не удалось сохранить состояние кота: {e}")

    def load_state(self):
        """Загрузка состояния кота"""
        try:
            with open('cat_state.json', 'r') as f:
                data = json.load(f)
                self.state.energy = data["energy"]
                self.state.happiness = data["happiness"]
                self.state.hunger = data["hunger"]
                self.state.last_update = data["last_update"]
        except:
            pass  # Используем значения по умолчанию

    def update(self, cursor_pos: Optional[Tuple[int, int]] = None) -> None:
        """Обновление состояния кота"""
        current_time = time.time()
        dt = current_time - self.state.last_update
        
        # Обновляем характеристики с учетом времени
        self.state.energy = max(0.0, min(100.0, self.state.energy - dt * 0.1 * self.personality.laziness))
        self.state.hunger = min(100.0, self.state.hunger + dt * 0.15)
        self.state.happiness = max(0.0, min(100.0, self.state.happiness - dt * 0.05))
        
        # Проверяем необходимость смены поведения
        if current_time - self.state.state_change_time > self._get_behavior_duration():
            self._choose_new_behavior(cursor_pos)
        
        self.state.last_update = current_time
        
        # Периодически сохраняем состояние
        if random.random() < 0.01:  # 1% шанс сохранения при каждом обновлении
            self.save_state()

    def _get_behavior_duration(self) -> float:
        """Получение длительности текущего поведения"""
        min_dur, max_dur = self.behaviors[self.current_behavior]['duration']
        return random.uniform(min_dur, max_dur)

    def _choose_new_behavior(self, cursor_pos: Optional[Tuple[int, int]]) -> None:
        """Выбор нового поведения кота"""
        # Принудительные состояния на основе потребностей
        if self.state.energy < 20:
            new_behavior = 'sleeping'
        elif self.state.hunger > 80:
            new_behavior = 'hunting'
        elif (cursor_pos and
              random.random() < self.personality.curiosity and
              self.current_behavior != 'sleeping'):
            new_behavior = 'hunting'
            self.state.target_x, self.state.target_y = cursor_pos
        else:
            # Вычисляем веса с учетом личности и состояния
            weights = {}
            for behavior, params in self.behaviors.items():
                weight = params['weight']
                
                # Модифицируем веса на основе личности и состояния
                if behavior == 'playing':
                    weight *= self.personality.playfulness * (self.state.energy / 100)
                elif behavior == 'sleeping':
                    weight *= self.personality.laziness * ((100 - self.state.energy) / 100)
                elif behavior == 'hunting':
                    weight *= self.personality.curiosity * (self.state.hunger / 100)
                
                weights[behavior] = weight
            
            # Выбираем новое поведение
            behaviors = list(weights.keys())
            behavior_weights = [weights[b] for b in behaviors]
            new_behavior = random.choices(behaviors, weights=behavior_weights)[0]
            
            # Определяем новую цель для движения
            if new_behavior in ['walking', 'hunting']:
                screen_width = 1920  # Примерная ширина экрана
                screen_height = 1080  # Примерная высота экрана
                self.state.target_x = random.randint(0, screen_width)
                self.state.target_y = random.randint(0, screen_height)
        
        self.current_behavior = new_behavior
        self.state.state_change_time = time.time()

class DesktopPet:
    """Основной класс для отображения и управления котом"""
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Desktop Cat")
        self.window.attributes('-topmost', True)
        self.window.overrideredirect(True)
        
        # Настраиваем прозрачность
        self.window.config(bg='white')
        self.window.attributes('-transparentcolor', 'white')
        
        # Создаем холст
        self.canvas = tk.Canvas(self.window, width=200, height=200,
                              bg='white', highlightthickness=0)
        self.canvas.pack()
        
        # Инициализируем ИИ кота
        self.cat_ai = CatAI()
        
        # Анимационные параметры
        self.animation_state = {
            'tail_angle': 0.0,
            'ear_angle': 0.0,
            'eye_size': 1.0,
            'breath_phase': 0.0,
            'direction': 1  # 1 - вправо, -1 - влево
        }
        
        # Физические параметры
        self.physics = {
            'position': [
                random.randint(0, self.window.winfo_screenwidth() - 200),
                random.randint(0, self.window.winfo_screenheight() - 200)
            ],
            'velocity': [0.0, 0.0],
            'acceleration': [0.0, 0.0]
        }
        
        # Устанавливаем начальную позицию
        self.window.geometry(
            f'+{int(self.physics["position"][0])}+{int(self.physics["position"][1])}'
        )
        
        # Привязываем события
        self.setup_events()
        
        # Запускаем анимацию
        self.animate()

    def setup_events(self):
        """Настройка обработчиков событий"""
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<Button-3>', self.feed_cat)
        self.canvas.bind('<Motion>', self.on_mouse_move)
        self.window.bind('<Key>', self.on_key)
        
        # Обработка закрытия окна
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    def draw_cat(self):
        """Отрисовка кота"""
        self.canvas.delete("all")
        
        # Цвета
        colors = {
            'main': "#FF8C00",    # рыжий
            'belly': "#FFFFFF",    # белый
            'eye': "#FFD700",     # жёлтый
            'nose': "#FFC0CB",    # розовый
            'whisker': "#FFFFFF"   # белый
        }
        
        # Параметры анимации
        breath = math.sin(self.animation_state['breath_phase']) * 3
        tail_wave = math.sin(self.animation_state['tail_angle'])
        
        # Модифицируем анимацию в зависимости от состояния
        if self.cat_ai.current_behavior == 'playing':
            tail_wave *= 2
        elif self.cat_ai.current_behavior == 'sleeping':
            tail_wave *= 0.2
        
        # Рисуем кота в зависимости от направления
        if self.animation_state['direction'] == 1:
            self._draw_cat_right(colors, breath, tail_wave)
        else:
            self._draw_cat_left(colors, breath, tail_wave)

    def _draw_cat_right(self, colors, breath, tail_wave):
        """Отрисовка кота, смотрящего вправо"""
        # Тело
        self.canvas.create_oval(70, 100 + breath, 
                              130, 160 + breath,
                              fill=colors['main'], outline=colors['main'])
        
        # Живот
        self.canvas.create_oval(85, 130 + breath,
                              115, 160 + breath,
                              fill=colors['belly'], outline=colors['belly'])
        
        # Голова
        self.canvas.create_oval(60, 60, 140, 120,
                              fill=colors['main'], outline=colors['main'])
        
        # Уши с анимацией
        ear_twitch = math.sin(self.animation_state['ear_angle']) * 5
        self.canvas.create_polygon(
            70 - ear_twitch, 60,
            85, 80,
            65 - ear_twitch, 80,
            fill=colors['main']
        )
        self.canvas.create_polygon(
            130 + ear_twitch, 60,
            140 + ear_twitch, 80,
            115, 80,
            fill=colors['main']
        )
        
        # Глаза и зрачки
        if self.cat_ai.current_behavior != 'sleeping':
            eye_h = 8 * self.animation_state['eye_size']
            
            # Левый глаз
            self.canvas.create_oval(75, 85 - eye_h/2,
                                  95, 85 + eye_h/2,
                                  fill=colors['eye'])
            # Правый глаз
            self.canvas.create_oval(105, 85 - eye_h/2,
                                  125, 85 + eye_h/2,
                                  fill=colors['eye'])
            
            # Зрачки с движением
            pupil_y = 85 + math.sin(time.time() * 2) * 2
            self.canvas.create_oval(82, pupil_y - 2,
                                  88, pupil_y + 2,
                                  fill="black")
            self.canvas.create_oval(112, pupil_y - 2,
                                  118, pupil_y + 2,
                                  fill="black")
        else:
            # Закрытые глаза
            self.canvas.create_line(75, 85, 95, 85, fill="black", width=2)
            self.canvas.create_line(105, 85, 125, 85, fill="black", width=2)
        
        # Нос
        self.canvas.create_polygon(97, 90, 103, 90, 100, 95,
                                 fill=colors['nose'])
        
        # Усы
        whisker_move = math.sin(self.animation_state['breath_phase']) * 2
        for i in range(3):
            # Левые усы
            self.canvas.create_line(70, 90 + i*5,
                                  40 + whisker_move, 85 + i*5,
                                  fill=colors['whisker'])
            # Правые усы
            self.canvas.create_line(130, 90 + i*5,
                                  160 - whisker_move, 85 + i*5,
                                  fill=colors['whisker'])
        
        # Хвост
        tail_x = 150 + tail_wave * 20
        tail_y = 120 + breath
        self.canvas.create_line(130, 140 + breath,
                              tail_x, tail_y,
                              fill=colors['main'], width=10,
                              smooth=True)

    def _draw_cat_left(self, colors, breath, tail_wave):
        """Отрисовка кота, смотрящего влево"""
        # Отзеркаливаем все x-координаты относительно центра (100)
        # Тело
        self.canvas.create_oval(130, 100 + breath, 
                              70, 160 + breath,
                              fill=colors['main'], outline=colors['main'])
        
        # Живот
        self.canvas.create_oval(115, 130 + breath,
                              85, 160 + breath,
                              fill=colors['belly'], outline=colors['belly'])
        
        # Голова
        self.canvas.create_oval(140, 60, 60, 120,
                              fill=colors['main'], outline=colors['main'])
        
        # Уши с анимацией
        ear_twitch = math.sin(self.animation_state['ear_angle']) * 5
        self.canvas.create_polygon(
            130 + ear_twitch, 60,
            115, 80,
            135 + ear_twitch, 80,
            fill=colors['main']
        )
        self.canvas.create_polygon(
            70 - ear_twitch, 60,
            60 - ear_twitch, 80,
            85, 80,
            fill=colors['main']
        )
        
        # Глаза и зрачки
        if self.cat_ai.current_behavior != 'sleeping':
            eye_h = 8 * self.animation_state['eye_size']
            
            # Левый глаз
            self.canvas.create_oval(125, 85 - eye_h/2,
                                  105, 85 + eye_h/2,
                                  fill=colors['eye'])
            # Правый глаз
            self.canvas.create_oval(95, 85 - eye_h/2,
                                  75, 85 + eye_h/2,
                                  fill=colors['eye'])
            
            # Зрачки с движением
            pupil_y = 85 + math.sin(time.time() * 2) * 2
            self.canvas.create_oval(118, pupil_y - 2,
                                  112, pupil_y + 2,
                                  fill="black")
            self.canvas.create_oval(88, pupil_y - 2,
                                  82, pupil_y + 2,
                                  fill="black")
        else:
            # Закрытые глаза
            self.canvas.create_line(125, 85, 105, 85, fill="black", width=2)
            self.canvas.create_line(95, 85, 75, 85, fill="black", width=2)
        
        # Нос
        self.canvas.create_polygon(103, 90, 97, 90, 100, 95,
                                 fill=colors['nose'])
        
        # Усы
        whisker_move = math.sin(self.animation_state['breath_phase']) * 2
        for i in range(3):
            # Левые усы
            self.canvas.create_line(130, 90 + i*5,
                                  160 - whisker_move, 85 + i*5,
                                  fill=colors['whisker'])
            # Правые усы
            self.canvas.create_line(70, 90 + i*5,
                                  40 + whisker_move, 85 + i*5,
                                  fill=colors['whisker'])
        
        # Хвост
        tail_x = 50 + tail_wave * 20
        tail_y = 120 + breath
        self.canvas.create_line(70, 140 + breath,
                              tail_x, tail_y,
                              fill=colors['main'], width=10,
                              smooth=True)

    def update_physics(self):
        """Обновление физики движения кота"""
        dt = 0.05  # Временной шаг
        
        if self.cat_ai.state.target_x is not None and self.cat_ai.state.target_y is not None:
            # Вычисляем вектор к цели
            dx = self.cat_ai.state.target_x - self.physics['position'][0]
            dy = self.cat_ai.state.target_y - self.physics['position'][1]
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance > 5:  # Если достаточно далеко от цели
                # Нормализуем направление
                dx /= distance
                dy /= distance
                
                # Задаем ускорение
                speed = 2.0 if self.cat_ai.current_behavior == 'hunting' else 1.0
                self.physics['acceleration'][0] = dx * speed
                self.physics['acceleration'][1] = dy * speed
                
                # Обновляем направление кота
                self.animation_state['direction'] = 1 if dx > 0 else -1
            else:
                self.physics['acceleration'] = [0.0, 0.0]
                self.cat_ai.state.target_x = None
                self.cat_ai.state.target_y = None
        
        # Применяем физику
        for i in range(2):
            # Обновляем скорость
            self.physics['velocity'][i] += self.physics['acceleration'][i] * dt
            # Добавляем трение
            self.physics['velocity'][i] *= 0.95
            # Обновляем позицию
            self.physics['position'][i] += self.physics['velocity'][i]
        
        # Проверяем границы экрана
        self.physics['position'][0] = max(0, min(self.physics['position'][0],
                                               self.window.winfo_screenwidth() - 200))
        self.physics['position'][1] = max(0, min(self.physics['position'][1],
                                               self.window.winfo_screenheight() - 200))
        
        # Обновляем позицию окна
        self.window.geometry(f'+{int(self.physics["position"][0])}+{int(self.physics["position"][1])}')

    def on_click(self, event):
        """Обработка клика мыши"""
        self.drag_x = event.x
        self.drag_y = event.y
        # Повышаем радость кота при поглаживании
        self.cat_ai.state.happiness = min(100, self.cat_ai.state.happiness + 10)
        print(f"Погладили котика! Радость: {self.cat_ai.state.happiness:.1f}")

    def on_drag(self, event):
        """Обработка перетаскивания"""
        new_x = self.window.winfo_x() + (event.x - self.drag_x)
        new_y = self.window.winfo_y() + (event.y - self.drag_y)
        self.physics['position'] = [float(new_x), float(new_y)]
        self.window.geometry(f'+{int(new_x)}+{int(new_y)}')

    def feed_cat(self, event):
        """Кормление кота"""
        self.cat_ai.state.hunger = max(0, self.cat_ai.state.hunger - 30)
        self.cat_ai.state.happiness = min(100, self.cat_ai.state.happiness + 10)
        print(f"Покормили котика! Голод: {self.cat_ai.state.hunger:.1f}")

    def on_mouse_move(self, event):
        """Обработка движения мыши"""
        screen_x = self.window.winfo_x() + event.x
        screen_y = self.window.winfo_y() + event.y
        if self.cat_ai.current_behavior == 'hunting':
            self.cat_ai.state.target_x = screen_x
            self.cat_ai.state.target_y = screen_y

    def on_key(self, event):
        """Обработка нажатий клавиш"""
        if event.char == 'q':
            self.on_closing()

    def on_closing(self):
        """Обработка закрытия приложения"""
        self.cat_ai.save_state()
        self.window.destroy()
        sys.exit()
    
    def run(self):
        """Запуск приложения"""
        try:
            self.window.mainloop()
        except Exception as e:
            print(f"Ошибка в главном цикле: {e}")
            self.on_closing()

    def animate(self):
        """Главный цикл анимации"""
        try:
            # Обновляем ИИ кота
            cursor_pos = None
            if self.window.winfo_pointerxy():
                cursor_pos = self.window.winfo_pointerxy()
            self.cat_ai.update(cursor_pos)
            
            # Обновляем физику
            self.update_physics()
            
            # Обновляем анимационные параметры
            self.animation_state['tail_angle'] += 0.2
            self.animation_state['breath_phase'] += 0.1
            
            # Случайные движения ушами
            if random.random() < 0.02:
                self.animation_state['ear_angle'] = random.random() * math.pi
            
            # Моргание
            if random.random() < 0.01:
                self.animation_state['eye_size'] = 0.2
            else:
                self.animation_state['eye_size'] = min(1.0, self.animation_state['eye_size'] + 0.2)
            
            # Отрисовка кота
            self.draw_cat()
            
            # Следующий кадр
            self.window.after(50, self.animate)
            
        except Exception as e:
            print(f"Ошибка в анимации: {e}")

def create_tray_icon():
    """Создание иконки в трее"""
    def create_icon(width, height, color="#FF8C00"):
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        dc.ellipse([4, 4, width-4, height-4], fill=color)
        return image

    def quit_window(icon):
        icon.stop()
        sys.exit()

    menu = (
        pystray.MenuItem('Выход', quit_window),
    )
    
    icon = pystray.Icon("name", create_icon(32, 32), "Desktop Cat", menu)
    return icon

def main():
    """Основная функция запуска приложения"""
    try:
        # Создаем и запускаем приложение
        icon = create_tray_icon()
        pet = DesktopPet()
        
        # Запускаем иконку в трее в отдельном потоке
        icon.run_detached()
        
        # Запускаем основное окно
        pet.run()
        
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()