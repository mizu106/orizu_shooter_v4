# pygbag対応
import asyncio
import math
import random
from pathlib import Path
import pygame

# 本編ここから
WIDTH, HEIGHT, FPS = 1000, 700, 60
ROOT = Path(__file__).resolve().parent
PLAY_TOP, PLAY_BOTTOM = 88, HEIGHT - 36
ENEMY_SIZE = 58
LIFE_ICON_SIZE = 42
# スマホ対応用変数
TOUCH_SHOOT_ZONE_X = WIDTH * 0.65
TOUCH_MOVE_SPEED = 1.0

# 初期化部
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bell Blossom Formation Shooter")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 34)       # 標準フォント
small_font = pygame.font.Font(None, 24) # 小さいフォント
big_font = pygame.font.Font(None, 72)   # 大きいフォント
tour_font = pygame.font.Font(ROOT / "NotoSansJP-Bold.ttf", 30)  # 日本語用フォント

# ツアー告知用テキストと表示タイミングの設定
TOUR_NOTICE_LINES = [
    "花魁道中 参周年記念 単独巡業",
    "「命の意味」",
    "",
    "11.01  【東京】浅草VAMPKIN",
    "11.03  【静岡】浜松FORCE",
    "11.07  【宮城】仙台spaceZero",
    "11.08  【栃木】HEAVEN'S ROCK 宇都宮2/3",
    "11.14  【愛知】名古屋DIVA",
    "11.15  【大阪】堺東Goith",
    "11.23  【福岡】福岡UTERO",
    "11.28  【群馬】高崎Club JAMMERS",
    "11.29  【千葉】柏ThumbUp",
    "12.07  【東京】ZeppDiverCity"
]
TOUR_LINE_DELAY = 0.28
TOUR_SLIDE_TIME = 0.65

# 画像読み込みとスケーリング用関数
def load_scaled(filename, max_w, max_h):
    image = pygame.image.load(ROOT / filename).convert_alpha()
    scale = min(max_w / image.get_width(), max_h / image.get_height())
    return pygame.transform.smoothscale(image, (int(image.get_width()*scale), int(image.get_height()*scale)))


PLAYER_IMAGE = load_scaled("player_flipped_transparent.png", 300, 310)
ENEMY_IMAGE = pygame.transform.smoothscale(
    pygame.image.load(ROOT / "Enemy-0001.png").convert_alpha(),
    (ENEMY_SIZE, ENEMY_SIZE),
)
LIFE_IMAGE = pygame.transform.smoothscale(
    pygame.image.load(ROOT / "Life-0001.png").convert_alpha(),
    (LIFE_ICON_SIZE, LIFE_ICON_SIZE),
)

# プレイヤークラス
class Player:
    def __init__(self):
        self.image = PLAYER_IMAGE
        self.rect = self.image.get_rect(midleft=(25, HEIGHT // 2))
        self.speed, self.hp = 370, 5
        self.shot_timer = self.invuln = 0.0

    @property
    def hitbox(self):
        return pygame.Rect(self.rect.centerx-28, self.rect.centery-38, 56, 76)

    def update(self, dt, keys):
        dx = int(bool(keys[pygame.K_RIGHT] or keys[pygame.K_d])) - int(bool(keys[pygame.K_LEFT] or keys[pygame.K_a]))
        dy = int(bool(keys[pygame.K_DOWN] or keys[pygame.K_s])) - int(bool(keys[pygame.K_UP] or keys[pygame.K_w]))
        if dx or dy:
            length = math.hypot(dx, dy)
            self.rect.x += int(dx / length * self.speed * dt)
            self.rect.y += int(dy / length * self.speed * dt)

        # 画面端処理の呼び出し
        self.keep_inside_screen()

        self.shot_timer = max(0, self.shot_timer - dt)
        self.invuln = max(0, self.invuln - dt)

    # 描画用メソッド
    def draw(self):
        if self.invuln <= 0 or int(self.invuln * 12) % 2 == 0:
            screen.blit(self.image, self.rect)
    
    # 画面端補正用メソッド
    def keep_inside_screen(self):
        box = self.hitbox

        if box.left < 0:
            self.rect.x -= box.left
        elif box.right > WIDTH:
            self.rect.x -= box.right - WIDTH

        box = self.hitbox

        if box.top < PLAY_TOP:
            self.rect.y += PLAY_TOP - box.top
        elif box.bottom > PLAY_BOTTOM:
            self.rect.y -= box.bottom - PLAY_BOTTOM

# 弾丸クラス
class Bullet:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y-14, 38, 28)
        self.speed = 760

    def update(self, dt): self.rect.x += int(self.speed * dt)

    def draw(self):
        x, y = self.rect.left, self.rect.centery
        pivot = (x+3, y)
        colors = [(214,53,72),(244,179,77),(248,232,157),(105,188,164),(74,126,154)]
        for i, color in enumerate(colors):
            a = -1.15 + i * 2.30 / len(colors)
            b = -1.15 + (i+1) * 2.30 / len(colors)
            p1 = (int(pivot[0]+math.cos(a)*31), int(pivot[1]+math.sin(a)*31))
            p2 = (int(pivot[0]+math.cos(b)*31), int(pivot[1]+math.sin(b)*31))
            pygame.draw.polygon(screen, color, [pivot, p1, p2])
        pygame.draw.arc(screen, (255,241,200), pygame.Rect(x-28,y-31,64,62), -1.15, 1.15, 3)
        pygame.draw.circle(screen, (117,67,45), pivot, 4)

# 敵クラス
class Enemy:
    """One formation member. Its final position is leader motion + local offset."""
    def __init__(self, formation, offset_x, offset_y, delay=0.0):
        self.formation = formation
        self.offset_x, self.offset_y, self.delay = offset_x, offset_y, delay
        self.image = ENEMY_IMAGE
        self.rect = self.image.get_rect()
        self.hp = formation.hp
        self.active = True
        self.sync_rect()

    def sync_rect(self):
        t = max(0.0, self.formation.age - self.delay)
        x, y = self.formation.position(t)
        self.rect.center = (round(x + self.offset_x), round(y + self.offset_y))

    def update(self):
        self.active = self.formation.age >= self.delay
        if self.active: self.sync_rect()

    def draw(self):
        if self.active: screen.blit(self.image, self.rect)

# 敵編隊のリーダークラス
class Formation:
    """Leader trajectory shared by all enemies in one formation."""
    def __init__(self, pattern, base_y, speed, hp):
        self.pattern, self.base_y, self.speed, self.hp = pattern, base_y, speed, hp
        self.age = 0.0
        self.start_x = WIDTH + 100
        self.phase = random.uniform(0, math.tau)

    def update(self, dt): self.age += dt

    def position(self, t):
        x = self.start_x - self.speed * t
        p = self.phase
        if self.pattern == "straight":
            y = self.base_y
        elif self.pattern == "sine":
            y = self.base_y + math.sin(t*3.2+p) * 72
        elif self.pattern == "wide_sine":
            y = self.base_y + math.sin(t*1.65+p) * 145
        elif self.pattern == "zigzag":
            period = 1.25
            q = ((t + p) % period) / period
            triangle = 1 - 4 * abs(q - 0.5)
            y = self.base_y + triangle * 95
        else:  # dive: enter level, sweep downward, then recover upward
            y = self.base_y + math.sin(t*1.35+p) * 35 + 115 * math.sin(min(t/3.2, 1.0)*math.pi)
        return x, max(PLAY_TOP+35, min(PLAY_BOTTOM-35, y))

# 敵編隊の形状定義
FORMATION_SHAPES = {
    "line": [(0,-72),(0,-36),(0,0),(0,36),(0,72)],
    "v": [(0,0),(54,-38),(54,38),(108,-76),(108,76)],
    "wedge": [(0,0),(48,-42),(48,42),(96,-84),(96,84),(96,0)],
    "diamond": [(0,0),(55,-50),(55,50),(110,0)],
    "stagger": [(0,-55),(42,0),(84,-55),(126,0),(168,-55)],
}
PATTERNS = ("straight", "sine", "wide_sine", "zigzag", "dive")

# 敵編隊の生成処理
def spawn_formation(level):
    pattern = random.choice(PATTERNS)
    shape_name = random.choice(tuple(FORMATION_SHAPES))
    margin = 145 if pattern in ("wide_sine", "dive") else 95
    base_y = random.randint(PLAY_TOP+margin, PLAY_BOTTOM-margin)
    leader = Formation(pattern, base_y, random.randint(120,170)+level*7, 1+level//5)
    # Small launch delays make staggered flights feel less rigid.
    members = [Enemy(leader, ox, oy, i*0.035) for i,(ox,oy) in enumerate(FORMATION_SHAPES[shape_name])]
    return leader, members

# ゲームのリセット処理
def reset():
    return Player(), [], [], [], 0, 0.0, 0.4, False

# ゲームオーバー画面の描画処理
def draw_game_over(game_over_elapsed):
    # ゲーム画面を暗くする半透明レイヤー
    shade = pygame.Surface(
        (WIDTH, HEIGHT),
        pygame.SRCALPHA,
    )
    shade.fill((10, 5, 18, 210))
    screen.blit(shade, (0, 0))

    # ゲームオーバー見出し
    title_surface = tour_font.render(
        "おいでなんし～",
        True,
        (255, 170, 210),
    )
    title_rect = title_surface.get_rect(
        center=(WIDTH // 2, 575),
    )
    screen.blit(title_surface, title_rect)

    # 告知表示位置
    notice_start_y = 50
    notice_spacing = 40

    # 1行ずつ右からスライドさせる
    for index, text in enumerate(TOUR_NOTICE_LINES):
        line_start_time = index * TOUR_LINE_DELAY

        progress = (
            game_over_elapsed - line_start_time
        ) / TOUR_SLIDE_TIME

        # この行の開始時刻になるまでは表示しない
        if progress < 0:
            continue

        # 1.0を超えないようにする
        progress = min(progress, 1.0)

        # 最初は速く、最後はゆっくり止まる
        eased = 1.0 - (1.0 - progress) ** 3

        # 最終行だけ色を変える
        if index == len(TOUR_NOTICE_LINES) - 1:
            text_color = (255, 110, 175)
        else:
            text_color = (255, 240, 250)

        text_surface = tour_font.render(
            text,
            True,
            text_color,
        )

        # 画面右外から中央へ移動
        start_x = WIDTH + text_surface.get_width()
        target_x = WIDTH // 2

        current_x = (
            start_x
            + (target_x - start_x) * eased
        )

        current_y = (
            notice_start_y
            + index * notice_spacing
        )

        text_rect = text_surface.get_rect(
            center=(int(current_x), current_y),
        )
        screen.blit(text_surface, text_rect)

    # リスタート案内
    restart_surface = small_font.render(
        "Press R to restart",
        True,
        (220, 210, 230),
    )
    restart_rect = restart_surface.get_rect(
        center=(WIDTH // 2, HEIGHT - 55),
    )
    screen.blit(restart_surface, restart_rect)

# Main関数
async def main():
    (
        player,
        bullets,
        enemies,
        formations,
        score,
        elapsed,
        wave_timer,
        game_over,
    ) = reset()
     
     # スマホ対応用初期化部
    touch_moving = False
    touch_shooting = False
    touch_target_x = 0
    touch_target_y = 0
    # ゲームオーバー時の経過時間を管理する変数
    game_over_elapsed = 0.0
    # ゲームループ制御用のフラグ
    running = True
    
    while running:
        dt = clock.tick(FPS) / 1000
        
        # イベントループ
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                # ゲームオーバー時のリセット処理
                if event.key == pygame.K_ESCAPE: running = False
                elif game_over and event.key == pygame.K_r:
                    (
                        player,
                        bullets,
                        enemies,
                        formations,
                        score,
                        elapsed,
                        wave_timer,
                        game_over,
                    ) = reset()
                    game_over_elapsed = 0.0

            # スマホ操作用前処理
            if event.type == pygame.FINGERDOWN:
                touch_x = event.x * WIDTH
                touch_y = event.y * HEIGHT

                if touch_x < TOUCH_SHOOT_ZONE_X:
                    touch_moving = True
                    touch_target_x = touch_x
                    touch_target_y = touch_y
                else:
                    touch_shooting = True
            # フリップ時の処理
            elif event.type == pygame.FINGERMOTION:
                touch_x = event.x * WIDTH
                touch_y = event.y * HEIGHT

                if touch_x < TOUCH_SHOOT_ZONE_X:
                    touch_moving = True
                    touch_target_x = touch_x
                    touch_target_y = touch_y
            # 指を話した時の処理
            elif event.type == pygame.FINGERUP:
                touch_x = event.x * WIDTH

                if touch_x < TOUCH_SHOOT_ZONE_X:
                    touch_moving = False
                else:
                    touch_shooting = False

        # 入力処理
        keys = pygame.key.get_pressed()
        if not game_over:
            elapsed += dt
            level = 1 + score // 2000
            # キーボード操作の座標移動処理
            player.update(dt, keys)
            # スマホのタッチ操作の座標移動処理
            if touch_moving:
                target_x = int(touch_target_x)
                target_y = int(touch_target_y)

                dx = target_x - player.hitbox.centerx
                dy = target_y - player.hitbox.centery

                distance = math.hypot(dx, dy)

                if distance > 5:
                    move_distance = min(
                        player.speed * dt,
                        distance,
                    )

                    player.rect.x += int(
                        dx / distance * move_distance
                    )

                    player.rect.y += int(
                        dy / distance * move_distance
                    )

                # 画面端チェック処理呼び出し
                player.keep_inside_screen()

            # キーボードでのショット処理
            # if (keys[pygame.K_SPACE] or keys[pygame.K_z]) and player.shot_timer <= 0:
            # スマホのショット処理追加版
            if (keys[pygame.K_SPACE] or keys[pygame.K_z] or touch_shooting) and player.shot_timer <= 0:
                bullets.append(Bullet(player.hitbox.right+60, player.hitbox.centery-80))
                player.shot_timer = 0.16

            # 敵のウェーブ生成処理
            wave_timer -= dt
            if wave_timer <= 0:
                formation, members = spawn_formation(level)
                formations.append(formation)
                enemies.extend(members)
                wave_timer = max(1.15, 2.6 - level*0.08)

            for f in formations: f.update(dt)
            for b in bullets: b.update(dt)
            for e in enemies: e.update()

            # 弾丸と敵の当たり判定処理
            for b in bullets[:]:
                hit = next((e for e in enemies if e.active and b.rect.colliderect(e.rect)), None)
                if hit:
                    hit.hp -= 1
                    bullets.remove(b)
                    if hit.hp <= 0:
                        enemies.remove(hit)
                        score += 100
            # 画面外の弾丸を削除する処理
            bullets[:] = [b for b in bullets if b.rect.left < WIDTH]
            for e in enemies[:]:
                if e.active and e.rect.right < 0:
                    enemies.remove(e)
                elif e.active and player.invuln <= 0 and e.rect.colliderect(player.hitbox):
                    enemies.remove(e)
                    player.hp -= 1
                    player.invuln = 1.2

            formations[:] = [f for f in formations if any(e.formation is f for e in enemies)]
            if player.hp <= 0:
                game_over = True
        # ゲームオーバー時の経過時間更新処理
        else:
            game_over_elapsed += dt
        
        # 現在の更新処理
        screen.fill((19,15,38))
        pygame.draw.rect(screen,(56,31,78),(0,80,WIDTH,5))
        pygame.draw.rect(screen,(190,64,112),(0,85,WIDTH,2))
        for b in bullets: b.draw()
        for e in enemies: e.draw()
        
        # スマホ操作用半透明ボタン
        touch_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA,)
        pygame.draw.circle(touch_layer, (255, 255, 255, 45), (110, HEIGHT - 115), 75, 4, )
        pygame.draw.circle(touch_layer, (255, 100, 160, 80), (WIDTH - 105, HEIGHT - 115), 68, )
        
        shoot_text = small_font.render("SHOT", True, (255, 255, 255), )
        touch_layer.blit(shoot_text, shoot_text.get_rect(center=(WIDTH - 105, HEIGHT - 115, )),)
        screen.blit(touch_layer, (0, 0))
        
        # 現在の描画処理
        player.draw()
        screen.blit(font.render(f"SCORE  {score:06d}",True,(255,240,250)),(24,22))
        screen.blit(font.render("LIFE",True,(255,105,155)),(350,25))
        for life_index in range(max(0, player.hp)):
            life_x = 425 + life_index * (LIFE_ICON_SIZE + 6)
            screen.blit(LIFE_IMAGE, (life_x, 17))
        screen.blit(small_font.render("MOVE: Arrow / WASD    SHOT: Space / Z    EXIT: Esc",True,(205,195,225)),(24,HEIGHT-29))
        # ゲームオーバー時の描画処理
        if game_over:
            draw_game_over(game_over_elapsed)

        # 画面更新処理
        pygame.display.flip()

        # ブラウザーへ処理を戻す
        await asyncio.sleep(0)
asyncio.run(main())
