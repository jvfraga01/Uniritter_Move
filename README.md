# Totem de Agachamentos — protótipo (PC)

Conta agachamentos pela webcam usando MediaPipe Pose e desbloqueia
achievements por volume total de reps. Este é o protótipo de mesa; a
mesma lógica de domínio deve rodar sem alterações quando isso virar um
totem físico (só a câmera e a UI de exibição mudam).

## Por que essa arquitetura

O projeto é dividido em camadas para que a parte que **importa de verdade**
— contar direito e não deixar passar rep errado — seja testável sem
precisar de webcam, mediapipe, ou nem sequer rodar no computador certo:

```
webcam (capture.py)
   -> mediapipe (pose_estimator.py)
   -> (hip_y, pose_height) (pose_metrics.py)
   -> StandingBaseline: calibração automática da postura "em pé"
   -> razão de queda do quadril, suavizada (smoothing.py)
   -> SquatCounter (squat_counter.py)      <- lógica pura, 100% testada
   -> AchievementEngine (achievements.py)  <- lógica pura, 100% testada
   -> storage.py (persiste em JSON)
   -> overlay.py (desenha na tela)
```

`squat_counter.py`, `pose_metrics.py`, `smoothing.py` e `achievements.py`
não importam `cv2` nem `mediapipe`. Eles recebem números (posições,
contagens) e devolvem números/eventos. Isso é o que permite testar toda a
lógica de "o que conta como agachamento válido" e "quando desbloquear um
achievement" em milissegundos, sem câmera.

## Como o agachamento é detectado

Em vez de calcular o ângulo do joelho (que exige ver joelho + tornozelo
com boa confiança — algo que uma webcam de mesa comum frequentemente não
enquadra), usamos a queda vertical do quadril:

1. **Calibração automática:** nos primeiros ~15 frames (assumindo que a
   pessoa está parada em pé), `StandingBaseline` grava a posição do
   quadril e a altura da pose detectada como referência ("baseline").
   Essa calibração continua se ajustando devagar sempre que o app
   confirma que a pessoa voltou a ficar em pé — então cada pessoa nova
   que usa o totem é recalibrada sozinha, sem botão.
2. A cada frame, calculamos `drop_ratio = (quadril_atual - quadril_baseline) / altura_da_pose_baseline`.
   Ex.: 0.35 = o quadril desceu 35% da altura da pose de pé.
3. Esse valor passa por uma suavização (`MovingAverage`, `src/smoothing.py`)
   pra ignorar tremores de 1-2 frames.
4. `SquatCounter` usa uma máquina de estados (em pé → descendo → fundo →
   subindo) sobre esse valor suavizado: só conta o rep se a pessoa
   realmente passou do `bottom_threshold` (35% por padrão) antes de
   voltar pra perto da baseline.

Quadril e ombros ficam visíveis na câmera com muito mais frequência do
que joelho/tornozelo, então esse método é bem mais robusto a
enquadramentos de webcam comuns (câmera alta, vendo só da cintura pra
cima).

## Como rodar o protótipo

### Windows, sem Python instalado: dois cliques

Dê dois cliques em `iniciar.bat` na raiz do projeto. Na primeira vez ele
baixa um Python portátil (não mexe no Python do sistema, se houver um),
instala as dependências e o modelo de pose, e já abre o programa. Da
segunda vez em diante pula tudo que já está pronto e abre na hora — não
precisa mais de internet depois da primeira execução completa.

### Manual (Linux/Mac ou quem já tem Python)

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m tools.download_model  # baixa o modelo (uma vez só, ~5 MB)
python main.py                  # abre a webcam, mostra contador na tela
# pressione 'q' para sair
```

> **Nota sobre a API do mediapipe:** usamos a Tasks API
> (`mediapipe.tasks.python.vision.PoseLandmarker`), não a antiga
> `mediapipe.solutions`. O Google descontinuou `solutions` em 2023, e em
> várias versões recentes do pacote (incluindo a 1.0.1) esse módulo vem
> quebrado/ausente no Windows -- é um bug conhecido e recorrente do
> próprio pacote (várias issues abertas no repositório oficial). A Tasks
> API não depende disso e funciona com qualquer versão recente do
> mediapipe.

O estado (total de agachamentos + achievements desbloqueados) é salvo em
`data/state.json` e recarregado automaticamente na próxima execução.

## Como rodar os testes

```bash
pip install -r requirements.txt   # ou só `pip install pytest` se quiser testar sem instalar mediapipe/opencv
pytest
```

Os testes de `tests/test_squat_counter.py`, `test_pose_metrics.py`,
`test_smoothing.py`, `test_achievements.py`, `test_geometry.py` e
`test_storage.py` **não precisam de webcam nem de mediapipe instalado**
— só testam a lógica pura.

## O "harness" de replay

`tools/record_session.py` grava, frame a frame, o ângulo real do joelho
durante uma sessão de webcam num CSV (`t_seconds,knee_angle`). Isso serve
para capturar dados de movimento real (com todo o jitter/ruído do
mediapipe) uma única vez, e depois reusar esse CSV em testes de regressão
sem precisar ligar a câmera de novo — veja
`tests/test_squat_counter_replay.py`, que já roda contra um CSV sintético
de exemplo (`tests/fixtures/sample_squat_sequence.csv`, 5 reps).

Fluxo sugerido quando for calibrar os thresholds de ângulo com uma pessoa
de verdade:

```bash
python -m tools.record_session --out tests/fixtures/sessao_real_joao.csv
```

Depois aponte um teste para esse CSV e trave o número de reps esperado —
vira um teste de regressão que protege contra "eu mudei um threshold e
agora ele conta agachamento errado".

## Ajustando a sensibilidade

Em `src/squat_counter.py`, `SquatCounterConfig`:

- `standing_threshold` (padrão 0.10 = 10%): abaixo disso é "em pé",
  perto da baseline calibrada.
- `bottom_threshold` (padrão 0.35 = 35%): acima disso é "profundidade
  válida" — só conta o rep se o quadril realmente desceu até aqui.
  Quer um agachamento mais raso/mais fundo pra contar? Sobe ou desce
  esse número.
- `min_frames_at_bottom` (padrão 1): aumente se o mediapipe estiver
  "tremendo" perto do fundo do movimento e gerando contagens falsas.

Em `src/pose_metrics.py`, `StandingBaseline`:

- `warmup_frames` (padrão 15): quantos frames iniciais usar pra
  calibração inicial. Aumente se a calibração estiver saindo ruim (ex.:
  o app iniciou bem no momento em que a câmera capturou um movimento).
- `smoothing` (padrão 0.15): o quanto cada novo frame "em pé" ajusta a
  baseline depois da calibração inicial. Aumente se a pessoa se afastar/
  aproximar da câmera durante o uso e a baseline precisar se adaptar mais
  rápido.

## Próximos passos (quando for virar totem de verdade)

1. Trocar `WebcamSource` por uma fonte de câmera dedicada, se necessário
   (a interface já é isolada em `src/capture.py`).
2. Trocar a janela OpenCV por uma UI em tela cheia/kiosk.
3. Se quiser achievements por sessão/dia (não só total acumulado), estender
   `storage.py` para guardar histórico por data — a lógica de
   `AchievementEngine` já aceita qualquer lista de `Achievement`.
4. Se quiser combinar sinais (ex.: queda do quadril + ângulo do joelho
   quando as pernas estiverem visíveis) pra mais robustez, `geometry.py`
   ainda tem `angle_3pts` disponível como utilitário puro e testado.
