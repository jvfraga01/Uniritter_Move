# squat-totem — regras para o Claude Code

## O que é este projeto
Contador de agachamentos por webcam (MediaPipe Pose). É um protótipo de
mesa hoje, mas vai virar um totem físico depois — a lógica de domínio
(contagem, calibração, achievements) não pode mudar quando isso
acontecer, só a captura de câmera e a UI.

## Regra de ouro da arquitetura (não quebrar isso)
Os módulos de lógica pura — `src/squat_counter.py`, `src/pose_metrics.py`,
`src/smoothing.py`, `src/achievements.py`, `src/geometry.py` — NUNCA
importam `cv2` nem `mediapipe`. Eles só recebem números (posições,
contagens) e devolvem números/eventos. É isso que permite testar 100%
da lógica "o que conta como agachamento válido" sem precisar de webcam.

Se uma tarefa parecer exigir que um desses arquivos importe cv2/mediapipe,
pare e avise antes de fazer — provavelmente a lógica nova pertence a
`pose_estimator.py`, `capture.py` ou `main.py`.

## Fluxo de trabalho esperado: plan → implement → test → validate
1. **Plan**: antes de editar código, explique o plano em texto — qual
   arquivo muda, por quê, e qual teste vai provar que funciona. Para
   mudanças que tocam mais de um módulo, prefiro revisar o plano antes
   de você editar (use plan mode).
2. **Implement**: mude o mínimo necessário para a tarefa. Siga o estilo
   já usado nos arquivos (dataclasses, type hints, docstring curta no
   topo do módulo explicando o "porquê", não só o "o quê").
3. **Test**: depois de QUALQUER mudança em `src/`, rode `pytest` e mostre
   o resultado. Uma tarefa com teste vermelho não está terminada.
4. **Validate**: se a mudança mexe em limiares de detecção
   (`standing_threshold`, `bottom_threshold`, calibração em
   `StandingBaseline`), rode contra os CSVs de `tests/fixtures/` (o
   harness de replay: `tools/record_session.py` grava sessões reais,
   `tests/test_squat_counter_replay.py` testa contra elas). Se a mudança
   cobre um cenário sem CSV real correspondente, avise que vale gravar
   um novo com `python -m tools.record_session`.
5. **Iterate**: se um bug aparecer em uso real, o primeiro passo é
   escrever um teste que reproduz o bug (de preferência com um CSV de
   replay), só depois corrigir.

## Comandos úteis
- Rodar testes: `pytest`
- Rodar o app: `python main.py`
- Baixar modelo (uma vez): `python -m tools.download_model`
- Gravar sessão real para virar teste de regressão:
  `python -m tools.record_session --out tests/fixtures/<nome>.csv`

## O que NÃO fazer
- Não considerar a tarefa pronta sem rodar `pytest`.
- Não adicionar dependência nova em `requirements.txt` sem justificar.
- Não misturar lógica de captura/exibição (cv2, janela, teclado) com
  lógica de decisão (contagem, achievements, calibração) no mesmo
  arquivo.
