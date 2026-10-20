from pygame import *
import socket
import json
import os
import random
from threading import Thread

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ---ПУГАМЕ НАЛАШТУВАННЯ ---
WIDTH, HEIGHT = 800, 600
init()
mixer.init()
screen = display.set_mode((WIDTH, HEIGHT))
clock = time.Clock()
display.set_caption("Пінг-Понг")

# --- ШРИФТИ ---
font_title = font.Font(None, 110)
font_win = font.Font(None, 72)
font_main = font.Font(None, 36)
font_small = font.Font(None, 26)

WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
PURPLE = (160, 120, 255)

# --- ЗОБРАЖЕННЯ ----
def load_img(name, size=None):
    pic = image.load("images/" + name).convert_alpha()
    if size:
        pic = transform.scale(pic, size)
    return pic


background = load_img("background.png", (WIDTH, HEIGHT))
menu_bg = load_img("menu_bg.png", (WIDTH, HEIGHT))
btn_img = load_img("button.png", (260, 64))
btn_hover_img = load_img("button_hover.png", (260, 64))
coin_img = load_img("coin.png", (24, 24))
coin_small = load_img("coin.png", (18, 18))

ball_skins = {
    "white": ["Класичний", 0],
    "tennis": ["Тенісний", 15],
    "fire": ["Вогняний", 30],
    "ice": ["Крижаний", 30],
    "gold": ["Золотий", 60],
}
paddle_skins = {
    "green": ["Зелена", 0],
    "purple": ["Фіолетова", 15],
    "wood": ["Дерев'яна", 20],
    "neon": ["Неон", 40],
    "red": ["Червона", 40],
}

ball_images = {}
ball_icons = {}
for name in ball_skins:
    ball_images[name] = load_img("ball_" + name + ".png", (20, 20))
    ball_icons[name] = load_img("ball_" + name + ".png", (40, 40))
paddle_images = {}
for name in paddle_skins:
    paddle_images[name] = load_img("paddle_" + name + ".png", (20, 100))

# --- ЗВУКИ ---
sounds = {}
for name in ["wall", "hit", "click", "coin", "goal", "win"]:
    sounds[name] = mixer.Sound("sounds/" + name + ".wav")
    sounds[name].set_volume(0.6)


SAVE_FILE = "save.json"
data = {
    "name": "Гравець",
    "coins": 0,
    "sound": True,
    "balls": ["white"],
    "paddles": ["green"],
    "ball": "white",
    "paddle": "green",
}
if os.path.exists(SAVE_FILE):
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data.update(json.load(f))
    except:
        pass


def save_game():
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def play(name):
    if data["sound"]:
        sounds[name].play()


def text(t, f, color, center):
    img = f.render(t, True, color)
    screen.blit(img, img.get_rect(center=center))


def draw_coins():
    screen.blit(coin_img, (WIDTH - 110, 18))
    t = font_main.render(str(data["coins"]), True, GOLD)
    screen.blit(t, (WIDTH - 80, 20))


class Button:
    def __init__(self, text, x, y):
        self.text = text
        self.rect = Rect(x, y, 260, 64)

    def draw(self):
        if self.rect.collidepoint(mouse.get_pos()):
            screen.blit(btn_hover_img, self.rect)
        else:
            screen.blit(btn_img, self.rect)
        text(self.text, font_main, WHITE, self.rect.center)

    def clicked(self, e):
        if e.type == MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            play("click")
            return True
        return False


# --- СЕРВЕР ---
client = None
my_id = 0
game_state = {}
buffer = ""
search_id = 0
sound_queue = []


def connect_to_server(my_try):
    global client, my_id, buffer, game_state
    while search_id == my_try and client is None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 8080))
            first = sock.recv(24).decode()
            while "\n" not in first:
                first += sock.recv(24).decode()
            line, buffer = first.split("\n", 1)
            my_id = int(line)
            game_state = {}
            client = sock
        except:
            time.wait(500)
    if client is not None and search_id == my_try:
        receive(client)


def receive(sock):
    global buffer, game_state
    while client is sock:
        try:
            d = sock.recv(1024).decode()
            if not d:
                raise ConnectionError
            buffer += d
            while "\n" in buffer:
                packet, buffer = buffer.split("\n", 1)
                if packet.strip():
                    game_state = json.loads(packet)
                    if game_state.get("sound_event"):
                        sound_queue.append(game_state["sound_event"])
        except:
            if client is sock:
                game_state["winner"] = -1
            break


def leave_game():
    global client, search_id
    search_id += 1
    if client:
        try:
            client.close()
        except:
            pass
    client = None


def start_search():
    global state, game_state, last_scores
    leave_game()
    game_state = {}
    last_scores = None
    sound_queue.clear()
    particles.clear()
    trail.clear()
    state = "wait"
    Thread(target=connect_to_server, args=(search_id,), daemon=True).start()


particles = []
trail = []
flash = 0


def spawn(x, y, n, color):
    for i in range(n):
        particles.append([x, y, random.uniform(-4, 4), random.uniform(-4, 4), random.randint(15, 30), color])


def draw_particles():
    for p in particles[:]:
        p[0] += p[2]
        p[1] += p[3]
        p[4] -= 1
        if p[4] <= 0:
            particles.remove(p)
            continue
        draw.circle(screen, p[5], (int(p[0]), int(p[1])), max(1, p[4] // 7))


play_btn = Button("Грати", 270, 220)
shop_btn = Button("Магазин", 270, 300)
settings_btn = Button("Налаштування", 270, 380)
exit_btn = Button("Вихід", 270, 460)
menu_ball = [100, 300, 4, 3]


def menu_screen(events):
    global state
    screen.blit(menu_bg, (0, 0))

    menu_ball[0] += menu_ball[2]
    menu_ball[1] += menu_ball[3]
    if menu_ball[0] < 10 or menu_ball[0] > WIDTH - 10:
        menu_ball[2] *= -1
    if menu_ball[1] < 10 or menu_ball[1] > HEIGHT - 10:
        menu_ball[3] *= -1
    screen.blit(ball_images[data["ball"]], (menu_ball[0] - 10, menu_ball[1] - 10))

    text("PING PONG", font_title, (60, 30, 120), (WIDTH // 2 + 4, 104))
    text("PING PONG", font_title, WHITE, (WIDTH // 2, 100))
    text("Привіт, " + data["name"] + "!", font_main, PURPLE, (WIDTH // 2, 170))
    draw_coins()

    for b in [play_btn, shop_btn, settings_btn, exit_btn]:
        b.draw()

    for e in events:
        if play_btn.clicked(e):
            start_search()
        if shop_btn.clicked(e):
            state = "shop"
        if settings_btn.clicked(e):
            state = "settings"
        if exit_btn.clicked(e):
            leave_game()
            exit()


name_box = Rect(250, 190, 300, 54)
sound_btn = Button("", 270, 290)
back_btn = Button("Назад", 270, 400)


def settings_screen(events):
    global state
    screen.blit(menu_bg, (0, 0))
    text("Налаштування", font_win, WHITE, (WIDTH // 2, 80))
    text("Ім'я гравця:", font_main, PURPLE, (WIDTH // 2, 165))

    draw.rect(screen, (30, 20, 60), name_box, border_radius=10)
    draw.rect(screen, PURPLE, name_box, 3, border_radius=10)
    cursor = "|" if time.get_ticks() // 500 % 2 else ""
    text(data["name"] + cursor, font_main, WHITE, name_box.center)

    sound_btn.text = "Звук: " + ("увімк" if data["sound"] else "вимк")
    sound_btn.draw()
    back_btn.draw()

    for e in events:
        if e.type == TEXTINPUT and len(data["name"]) < 12:
            data["name"] += e.text
        if e.type == KEYDOWN and e.key == K_BACKSPACE:
            data["name"] = data["name"][:-1]
        if sound_btn.clicked(e):
            data["sound"] = not data["sound"]
        if back_btn.clicked(e) or (e.type == KEYDOWN and e.key in [K_ESCAPE, K_RETURN]):
            if not data["name"].strip():
                data["name"] = "Гравець"
            save_game()
            state = "menu"


shop_back_btn = Button("Назад", 270, 522)
shop_msg = ""
shop_msg_time = 0


def shop_row(events, skins, images, owned_key, select_key, y, h, title):
    global shop_msg, shop_msg_time
    text(title, font_main, PURPLE, (WIDTH // 2, y - 18))
    x = 70
    for name in skins:
        skin_name, price = skins[name]
        card = Rect(x, y, 120, h)
        if card.collidepoint(mouse.get_pos()):
            draw.rect(screen, (70, 50, 130), card, border_radius=12)
        else:
            draw.rect(screen, (40, 30, 80), card, border_radius=12)
        if data[select_key] == name:
            draw.rect(screen, GOLD, card, 3, border_radius=12)

        pic = images[name]
        screen.blit(pic, pic.get_rect(center=(card.centerx, card.y + (h - 50) // 2)))
        text(skin_name, font_small, WHITE, (card.centerx, card.bottom - 40))

        if data[select_key] == name:
            text("Обрано", font_small, GOLD, (card.centerx, card.bottom - 16))
        elif name in data[owned_key]:
            text("Вибрати", font_small, (150, 255, 150), (card.centerx, card.bottom - 16))
        else:
            screen.blit(coin_small, (card.centerx - 24, card.bottom - 25))
            p = font_small.render(str(price), True, GOLD)
            screen.blit(p, (card.centerx - 2, card.bottom - 24))

        for e in events:
            if e.type == MOUSEBUTTONDOWN and e.button == 1 and card.collidepoint(e.pos):
                if name in data[owned_key]:
                    data[select_key] = name
                    play("click")
                elif data["coins"] >= price:
                    data["coins"] -= price
                    data[owned_key].append(name)
                    data[select_key] = name
                    play("coin")
                    shop_msg = "Куплено: " + skin_name
                    shop_msg_time = time.get_ticks()
                else:
                    shop_msg = "Не вистачає монет!"
                    shop_msg_time = time.get_ticks()
                save_game()
        x += 135


def shop_screen(events):
    global state
    screen.blit(menu_bg, (0, 0))
    text("Магазин", font_win, WHITE, (WIDTH // 2, 40))
    draw_coins()

    shop_row(events, ball_skins, ball_icons, "balls", "ball", 140, 120, "М'ячі")
    shop_row(events, paddle_skins, paddle_images, "paddles", "paddle", 305, 200, "Платформи")

    if time.get_ticks() - shop_msg_time < 1500:
        text(shop_msg, font_main, GOLD, (WIDTH // 2, 85))

    shop_back_btn.draw()
    for e in events:
        if shop_back_btn.clicked(e) or (e.type == KEYDOWN and e.key == K_ESCAPE):
            state = "menu"


def wait_screen(events):
    global state
    screen.blit(menu_bg, (0, 0))
    dots = "." * (time.get_ticks() // 400 % 4)
    text("Очікування гравців" + dots, font_main, WHITE, (WIDTH // 2, HEIGHT // 2))
    text("ESC - назад", font_small, PURPLE, (WIDTH // 2, HEIGHT // 2 + 50))
    if game_state:
        state = "game"
    for e in events:
        if e.type == KEYDOWN and e.key == K_ESCAPE:
            leave_game()
            state = "menu"


# --- ГРА ---
last_scores = None
you_winner = False
reward = 0


def game_screen(events):
    global state, last_scores, flash, you_winner, reward
    gs = game_state

    if gs.get("winner") is not None:
        you_winner = gs["winner"] == my_id
        reward = 10 if you_winner else 3
        data["coins"] += reward
        save_game()
        play("win" if you_winner else "goal")
        state = "end"
        return

    screen.blit(background, (0, 0))
    if "paddles" not in gs:
        return

    my_skin = data["paddle"]
    enemy_skin = "purple" if my_skin != "purple" else "green"
    left = my_skin if my_id == 0 else enemy_skin
    right = my_skin if my_id == 1 else enemy_skin
    screen.blit(paddle_images[left], (20, gs["paddles"]["0"]))
    screen.blit(paddle_images[right], (WIDTH - 40, gs["paddles"]["1"]))

    bx, by = gs["ball"]["x"], gs["ball"]["y"]
    if trail and abs(trail[-1][0] - bx) > 60:
        trail.clear()
    trail.append((bx, by))
    if len(trail) > 8:
        trail.pop(0)
    ball_img = ball_images[data["ball"]]
    for i, (tx, ty) in enumerate(trail[:-1]):
        t = ball_img.copy()
        t.set_alpha(20 + i * 20)
        screen.blit(t, (tx - 10, ty - 10))
    screen.blit(ball_img, (bx - 10, by - 10))

    while sound_queue:
        ev = sound_queue.pop(0)
        if ev == "wall_hit":
            play("wall")
            spawn(bx, by, 6, (180, 180, 255))
        elif ev == "platform_hit":
            play("hit")
            spawn(bx, by, 14, (255, 200, 80))
    draw_particles()

    if last_scores is not None and gs["scores"] != last_scores:
        play("goal")
        flash = 12
    last_scores = list(gs["scores"])
    if flash > 0:
        s = Surface((WIDTH, HEIGHT), SRCALPHA)
        s.fill((255, 255, 255, flash * 8))
        screen.blit(s, (0, 0))
        flash -= 1

    text(f"{gs['scores'][0]} : {gs['scores'][1]}", font_win, WHITE, (WIDTH // 2, 30))
    my_x = 120 if my_id == 0 else WIDTH - 120
    enemy_x = WIDTH - 120 if my_id == 0 else 120
    text(data["name"], font_main, GOLD, (my_x, 30))
    text("Суперник", font_main, WHITE, (enemy_x, 30))

    if gs.get("countdown", 0) > 0:
        text(str(gs["countdown"]), font_title, GOLD, (WIDTH // 2, HEIGHT // 2))
        side = "зліва" if my_id == 0 else "справа"
        text("Ти граєш " + side + "  (W / S)", font_main, WHITE, (WIDTH // 2, HEIGHT // 2 + 70))
        return

    keys = key.get_pressed()
    try:
        if keys[K_w] or keys[K_UP]:
            client.send(b"UP")
        elif keys[K_s] or keys[K_DOWN]:
            client.send(b"DOWN")
    except:
        pass


end_btn = Button("В меню", 270, 420)


def end_screen(events):
    global state
    screen.blit(menu_bg, (0, 0))
    if you_winner:
        text("Ти переміг!", font_win, GOLD, (WIDTH // 2, HEIGHT // 2 - 80))
    else:
        text("Пощастить наступним разом!", font_win, GOLD, (WIDTH // 2, HEIGHT // 2 - 80))
    screen.blit(coin_img, (WIDTH // 2 - 45, HEIGHT // 2 - 12))
    p = font_main.render("+" + str(reward), True, GOLD)
    screen.blit(p, (WIDTH // 2 - 12, HEIGHT // 2 - 10))
    text("K - в меню", font_small, PURPLE, (WIDTH // 2, HEIGHT // 2 + 50))
    end_btn.draw()
    for e in events:
        if end_btn.clicked(e) or (e.type == KEYDOWN and e.key == K_k):
            leave_game()
            state = "menu"


state = "menu"
while True:
    events = event.get()
    for e in events:
        if e.type == QUIT:
            leave_game()
            exit()

    if state == "menu":
        menu_screen(events)
    elif state == "settings":
        settings_screen(events)
    elif state == "shop":
        shop_screen(events)
    elif state == "wait":
        wait_screen(events)
    elif state == "game":
        game_screen(events)
    elif state == "end":
        end_screen(events)

    display.update()
    clock.tick(60)
