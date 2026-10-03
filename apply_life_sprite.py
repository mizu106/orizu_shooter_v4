from pathlib import Path

p = Path('main.py')
if not p.exists():
    raise SystemExit('main.py が見つかりません。v4のゲームフォルダー内で実行してください。')
s = p.read_text(encoding='utf-8')

if 'LIFE_ICON_SIZE = 42' not in s:
    s = s.replace('ENEMY_SIZE = 58\n', 'ENEMY_SIZE = 58\nLIFE_ICON_SIZE = 42\n')

enemy_block = '''ENEMY_IMAGE = pygame.transform.smoothscale(
    pygame.image.load(ROOT / "Enemy-0001.png").convert_alpha(),
    (ENEMY_SIZE, ENEMY_SIZE),
)
'''
life_block = '''LIFE_IMAGE = pygame.transform.smoothscale(
    pygame.image.load(ROOT / "Life-0001.png").convert_alpha(),
    (LIFE_ICON_SIZE, LIFE_ICON_SIZE),
)
'''
if 'LIFE_IMAGE =' not in s:
    if enemy_block not in s:
        raise SystemExit('敵画像の読み込み部分を検出できませんでした。v4のmain.pyを使用してください。')
    s = s.replace(enemy_block, enemy_block + life_block)

old = '''    screen.blit(font.render(f"SCORE  {score:06d}",True,(255,240,250)),(24,22))
    screen.blit(font.render("HP  "+"<3 "*max(0,player.hp),True,(255,105,155)),(360,22))
    screen.blit(small_font.render("MOVE: Arrow / WASD    SHOT: Space / Z    EXIT: Esc",True,(205,195,225)),(24,HEIGHT-29))
'''
new = '''    screen.blit(font.render(f"SCORE  {score:06d}",True,(255,240,250)),(24,22))
    screen.blit(font.render("LIFE",True,(255,105,155)),(350,25))
    for life_index in range(max(0, player.hp)):
        life_x = 425 + life_index * (LIFE_ICON_SIZE + 6)
        screen.blit(LIFE_IMAGE, (life_x, 17))
    screen.blit(small_font.render("MOVE: Arrow / WASD    SHOT: Space / Z    EXIT: Esc",True,(205,195,225)),(24,HEIGHT-29))
'''
if old in s:
    s = s.replace(old, new)
elif 'screen.blit(LIFE_IMAGE' not in s:
    raise SystemExit('残機表示部分を検出できませんでした。v4のmain.pyを使用してください。')

p.write_text(s, encoding='utf-8')
print('main.py の残機表示を Life-0001.png に変更しました。')
