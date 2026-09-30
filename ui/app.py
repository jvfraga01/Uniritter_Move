"""UniRitter Move - interface do totem (telas 1 a 4 da jornada).

Rodar (na raiz do projeto):  python -m ui.app
Teclas: Enter = botão principal | 1/2/3 = escolhe botão | Esc = voltar/sair
        F11 = tela cheia | dígitos/Backspace = RA (só para desenvolvimento)
Mouse simula o pulso: segure o cursor sobre um botão ~1 s.
"""
import subprocess
import sys
from pathlib import Path

import pygame

if sys.platform == "win32":  # sem isso o Windows com escala 125%/150% "estica" a janela
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

try:
    import cv2
except ImportError:  # a UI também abre sem câmera
    cv2 = None

ROOT = Path(__file__).resolve().parent.parent  # raiz do projeto (onde está main.py)
W, H = 1920, 1080
HOLD_S = 1.0
BG, WHITE, ACCENT, DIM = (18, 22, 30), (245, 247, 250), (255, 122, 26), (200, 205, 215)


def open_camera(preferred=0):
    """Tenta vários índices/backends (no Windows o DirectShow costuma funcionar melhor)."""
    if cv2 is None:
        return None, "OpenCV (cv2) não instalado neste Python"
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if sys.platform == "win32" else [cv2.CAP_ANY]
    for idx in [preferred] + [i for i in range(3) if i != preferred]:
        for be in backends:
            cap = cv2.VideoCapture(idx, be)
            if cap.isOpened():
                ok = False
                for _ in range(20):  # descarta os primeiros quadros (costumam vir pretos)
                    ok, frame = cap.read()
                    if ok and frame is not None and frame.mean() > 2:
                        break
                if ok:
                    return cap, f"Câmera {idx} ativa"
            cap.release()
    return None, "Nenhuma câmera encontrada (feche outros programas que usam a webcam)"


class Background:
    """Câmera espelhada e desfocada (desfoque barato: reduz, borra, amplia)."""

    def __init__(self, index=0):
        self.index = index
        self.cap, self.status = open_camera(index)
        print("[UI]", self.status)
        self.fails = 0
        self.frame = None  # último quadro (espelhado, BGR) para o rastreador de mãos
        self.surf = pygame.Surface((W, H))
        self.surf.fill(BG)

    def release(self):
        """Libera a webcam para o sistema de contagem poder usá-la."""
        if self.cap is not None:
            self.cap.release()
        self.cap, self.status = None, "Câmera liberada para o exercício"

    def reopen(self):
        self.cap, self.status = open_camera(self.index)
        self.fails = 0

    def update(self):
        if self.cap is None:
            return
        ok, frame = self.cap.read()
        if not ok or frame is None:
            self.fails += 1
            if self.fails > 60:
                self.status = "Câmera parou de responder"
            return
        self.fails = 0
        frame = cv2.flip(frame, 1)
        self.frame = frame
        small = cv2.GaussianBlur(cv2.resize(frame, (192, 108)), (0, 0), 4)
        big = cv2.convertScaleAbs(cv2.resize(small, (W, H)), alpha=0.45)  # escurece p/ contraste
        rgb = cv2.cvtColor(big, cv2.COLOR_BGR2RGB)
        self.surf = pygame.image.frombuffer(rgb.tobytes(), (W, H), "RGB")


class Button:
    def __init__(self, rect, label, hint, action):
        self.rect, self.label, self.hint, self.action = pygame.Rect(rect), label, hint, action
        self.hold, self.armed = 0.0, True

    def update(self, pos, dt):
        """True quando o cursor ficou HOLD_S s sobre o botão. Depois de acionar,
        só rearma quando o cursor sair do botão (evita ficar carregando em loop)."""
        over = bool(pos) and self.rect.collidepoint(pos)
        if over and self.armed:
            self.hold += dt
            if self.hold >= HOLD_S:
                self.hold, self.armed = 0.0, False
                return True
        else:
            self.hold = max(0.0, self.hold - 2 * dt)
            if not over:
                self.armed = True
        return False

    def draw(self, s, fonts):
        active = self.hold > 0
        pygame.draw.rect(s, ACCENT if active else (40, 48, 64), self.rect, border_radius=28)
        pygame.draw.rect(s, WHITE, self.rect, 3, border_radius=28)
        t = fonts["btn"].render(self.label, True, WHITE)
        s.blit(t, t.get_rect(center=(self.rect.centerx, self.rect.centery - 14)))
        h = fonts["small"].render(self.hint, True, DIM)
        s.blit(h, h.get_rect(center=(self.rect.centerx, self.rect.centery + 34)))
        if active:  # anel de progresso
            ring = pygame.Rect(0, 0, 90, 90)
            ring.midright = (self.rect.right - 30, self.rect.centery)
            pygame.draw.arc(s, WHITE, ring, -1.5708, -1.5708 + 6.2832 * self.hold / HOLD_S, 8)


class App:
    def __init__(self, pointer_factory=None, camera_index=0):
        pygame.init()
        self.full = False
        info = pygame.display.Info()  # tamanho real do monitor
        self.desk = (info.current_w, info.current_h)
        k = min(0.9 * self.desk[0] / W, 0.9 * self.desk[1] / H, 1.0)
        self.win = (int(W * k), int(H * k))  # janela 16:9 que cabe no monitor
        self.screen = pygame.display.set_mode(self.win, pygame.RESIZABLE)
        self.view = pygame.Rect(0, 0, *self.win)
        pygame.display.set_caption("UniRitter Move")
        self.canvas = pygame.Surface((W, H))
        self.fonts = {"title": pygame.font.SysFont("arial", 110, bold=True),
                      "sub": pygame.font.SysFont("arial", 56),
                      "btn": pygame.font.SysFont("arial", 64, bold=True),
                      "small": pygame.font.SysFont("arial", 34)}
        self.bg = Background(camera_index)
        self.pointer = pointer_factory((W, H)) if pointer_factory else None
        self.ra, self.mode, self.state = "", None, "home"
        self.notice, self.proc = ("", 0), None
        self.clock = pygame.time.Clock()
        if self.pointer is not None and not getattr(self.pointer, "window_space", False):
            pygame.mouse.set_visible(False)  # cursor é o dedo, não o mouse
        self.buttons = []
        self.go("home")

    # ---- telas -------------------------------------------------------
    def go(self, state):
        self.state = state
        cx, bw, bh = W // 2, 720, 170
        def btn(y, label, hint, action, w=bw):
            return Button((cx - w // 2, y, w, bh), label, hint, action)
        if state == "home":
            self.buttons = [btn(650, "COMEÇAR", "aponte e segure", lambda: self.go("id"))]
        elif state == "id":
            self.buttons = [btn(640, "CONTINUAR", "aponte e segure", self.submit_ra),
                            btn(840, "VOLTAR", "aponte e segure", lambda: self.go("home"))]
        elif state == "confirm":
            self.buttons = [btn(650, "ESCOLHER DESAFIO", "aponte e segure", lambda: self.go("mode"))]
        elif state == "mode":
            opts = [("META FIXA", "meta"), ("CONTRA O TEMPO", "tempo"), ("DESAFIO DO DIA", "dia")]
            self.buttons = [Button((120 + i * 620, 500, 560, 300), n,
                                   "disponível" if m == "meta" else "em breve",
                                   (lambda m=m: self.pick_mode(m))) for i, (n, m) in enumerate(opts)]
        elif state == "running":
            self.buttons = []

    def notify(self, msg, secs=3.5):
        self.notice = (msg, pygame.time.get_ticks() + int(secs * 1000))

    def submit_ra(self):
        if not self.ra:
            self.notify("Falta preencher a matrícula (RA) para continuar")
            return
        self.go("confirm")  # TODO: validar na base institucional / QR Code

    def pick_mode(self, m):
        if m != "meta":
            self.notify("Este modo ainda não está disponível. Por enquanto: Meta fixa")
            return
        self.mode = m
        self.launch_counter()

    def launch_counter(self):
        """Roda o sistema existente (o mesmo main.py do iniciar.bat) e espera ele fechar."""
        self.bg.release()  # só um programa por vez pode usar a webcam
        try:
            self.proc = subprocess.Popen([sys.executable, str(ROOT / "main.py")], cwd=str(ROOT))
        except OSError as err:
            self.proc = None
            self.bg.reopen()
            self.notify(f"Não consegui iniciar o main.py: {err}", 6)
            return
        self.go("running")

    def poll_counter(self):
        if self.proc is not None and self.proc.poll() is not None:
            code, self.proc = self.proc.returncode, None
            self.bg.reopen()
            self.go("home")
            if code:
                self.notify(f"O exercício terminou com erro (código {code}). Veja o terminal.", 6)

    def text(self, key, msg, y, color=WHITE):
        t = self.fonts[key].render(msg, True, color)
        self.canvas.blit(t, t.get_rect(center=(W // 2, y)))

    def draw_screen(self):
        s = self.state
        if s == "home":
            self.text("small", "UNIRITTER MOVE", 230, ACCENT)
            self.text("title", "Bora se movimentar?", 400)
            self.text("sub", "Aponte o dedo para o botão e segure", 540, DIM)
        elif s == "id":
            self.text("title", "IDENTIFIQUE-SE PARA PARTICIPAR", 200)
            self.text("sub", "Digite seu RA/matrícula (ou acesse via QR Code)", 350, DIM)
            field = pygame.Rect(W // 2 - 400, 440, 800, 120)
            pygame.draw.rect(self.canvas, WHITE, field, border_radius=20)
            t = self.fonts["btn"].render(self.ra or "_", True, BG)
            self.canvas.blit(t, t.get_rect(center=field.center))
        elif s == "confirm":
            self.text("title", "IDENTIFICAÇÃO REALIZADA", 330)
            self.text("sub", "Tudo pronto para começar!", 500, DIM)
        elif s == "mode":
            self.text("title", "ESCOLHA SEU DESAFIO", 250)
        elif s == "running":
            self.text("title", "EXERCÍCIO EM ANDAMENTO", 400)
            self.text("sub", "Faça os agachamentos na janela do exercício.", 540, DIM)
            self.text("sub", "Pressione Q nessa janela para encerrar.", 620, DIM)
        for b in self.buttons:
            b.draw(self.canvas, self.fonts)
        msg, until = self.notice
        if msg and pygame.time.get_ticks() < until:
            t = self.fonts["sub"].render(msg, True, BG)
            box = t.get_rect(center=(W // 2, 600)).inflate(80, 40)
            pygame.draw.rect(self.canvas, ACCENT, box, border_radius=20)
            self.canvas.blit(t, t.get_rect(center=box.center))
        st = self.fonts["small"].render(self.bg.status, True, DIM if self.bg.cap else ACCENT)
        self.canvas.blit(st, (30, H - 60))

    # ---- loop --------------------------------------------------------
    def screen_size(self):
        return pygame.display.get_surface().get_size()

    def handle_key(self, e):
        if e.key == pygame.K_F11:
            self.full = not self.full
            if self.full:
                pygame.display.set_mode(self.desk, pygame.FULLSCREEN)
            else:
                pygame.display.set_mode(self.win, pygame.RESIZABLE)
        elif e.key == pygame.K_ESCAPE:
            if self.state == "running":
                if self.proc is not None:
                    self.proc.terminate()
                return True
            if self.state == "home":
                return False
            self.go("home")
        elif e.key == pygame.K_RETURN and self.buttons:
            self.buttons[0].action()
        elif self.state == "id" and e.key == pygame.K_BACKSPACE:
            self.ra = self.ra[:-1]
        elif self.state == "id" and e.unicode.isdigit() and len(self.ra) < 12:
            self.ra += e.unicode
        elif e.unicode in "123" and e.unicode and self.state == "mode":
            self.buttons[int(e.unicode) - 1].action()
        return True

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(30) / 1000
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.KEYDOWN:
                    running = self.handle_key(e) is not False and running
            self.poll_counter()
            self.bg.update()
            if hasattr(self.pointer, "feed") and self.bg.frame is not None and self.bg.cap is not None:
                self.pointer.feed(self.bg.frame)
            p = self.pointer.get() if self.pointer else None
            if p and getattr(self.pointer, "window_space", False):  # mouse: corrige barras pretas
                v = self.view
                p = ((p[0] * self.screen_size()[0] - v.x) / v.w, (p[1] * self.screen_size()[1] - v.y) / v.h)
            pos = (int(p[0] * W), int(p[1] * H)) if p and 0 <= p[0] <= 1 and 0 <= p[1] <= 1 else None
            for b in list(self.buttons):
                if b.update(pos, dt):
                    b.action()
                    break
            self.canvas.blit(self.bg.surf, (0, 0))
            self.draw_screen()
            if pos:
                pygame.draw.circle(self.canvas, ACCENT, pos, 22)
                pygame.draw.circle(self.canvas, WHITE, pos, 22, 4)
            surf = pygame.display.get_surface()
            sw, sh = surf.get_size()
            k = min(sw / W, sh / H)
            vw, vh = int(W * k), int(H * k)
            self.view = pygame.Rect((sw - vw) // 2, (sh - vh) // 2, vw, vh)
            surf.fill((0, 0, 0))
            surf.blit(pygame.transform.smoothscale(self.canvas, (vw, vh)), self.view.topleft)
            pygame.display.flip()
        if self.proc is not None:
            self.proc.terminate()
        pygame.quit()


def make_pointer(size):
    """Dedo indicador como cursor; se falhar, cai para o mouse (modo desenvolvimento)."""
    from .inputs import HandPointer, MousePointer, ensure_hand_model
    try:
        return HandPointer(ensure_hand_model(ROOT))
    except Exception as err:
        print("[UI] Rastreio de mãos indisponível, usando mouse:", err)
        return MousePointer(size)


if __name__ == "__main__":
    App(pointer_factory=make_pointer).run()
    sys.exit(0)