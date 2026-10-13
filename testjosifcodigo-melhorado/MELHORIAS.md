# Melhorias aplicadas

> Depois de atualizar os arquivos, rode **uma vez**: `python manage.py migrate`
> (migrações novas: `0003` e `0004_atividade_data_conclusao`). Depois, `python manage.py test` para rodar os testes.

## Bugs corrigidos
- **Cronograma não mostrava nenhuma atividade**: o template esperava `atividades_por_dia`, mas a view enviava `semana`.
  A grade foi refeita; agora a navegação de semanas funciona (`?semana=`), as datas são reais, as estatísticas
  (horas planejadas e taxa de conclusão) deixaram de ser fixas em 0 e cada cartão tem botões de concluir e excluir.
- **Relatórios**: não havia como registrar um estudo pela interface (só a view existia). Adicionados o botão/modal
  "Registrar estudo", o filtro de período funcional, o gráfico por dia (antes imprimia a lista inteira em cada barra)
  e a distribuição por matéria baseada em tempo estudado. "Exportar PDF" agora usa a impressão do navegador.
- **Data do estudo ignorada**: `RegistroEstudo.data` usava `auto_now_add`, então a data escolhida era descartada.
- **Fuso horário**: "hoje" usava UTC; depois das 21h (Brasília) o dashboard mostrava o dia seguinte. Agora usa `localdate()`.
- **Trocar o e-mail impedia o login**: o `username` continuava sendo o e-mail antigo. Agora ele acompanha o e-mail
  (com checagem de e-mail já usado).
- **Duração das atividades** ignorava os minutos (09:00–09:45 = 0h).
- **Matérias ordenadas por prioridade** apareciam como Média → Baixa → Alta (ordenação alfabética do texto).
- **Avatar** só aparecia em Configurações; agora aparece na sidebar de todas as páginas.
- **Nível do dashboard** estava fixo em "Iniciante"; agora usa os pontos reais.
- **Cor do tema** era salva como `rgb(...)`, quebrando a seleção na tela; agora é normalizada para hexadecimal.

## Segurança
- Excluir (matéria, meta, atividade), concluir atividade e sair da conta agora exigem **POST** (antes eram links GET,
  vulneráveis a CSRF — um `<img src=".../delete/1/">` em outro site apagava dados).
- Editar meta aceitava `materia` de **outro usuário** (IDOR) e `int()` sem tratamento gerava erro 500.
- Upload de avatar valida tamanho (2 MB) e o conteúdo real da imagem, e apaga a foto anterior.
- `SECRET_KEY`, `DEBUG` e `ALLOWED_HOSTS` vêm de variáveis de ambiente (veja `.env.example`); em produção
  (`DJANGO_DEBUG=False`) os cookies passam a ser `Secure`.
- Redirecionamento `next` validado (open redirect) e `login` respeita `?next=`.

## Validações e qualidade
- Progresso entre 0–100, término depois do início, datas futuras barradas, e-mail único sem diferenciar maiúsculas.
- Mensagens de erro de cadastro com o nome do campo ("Senha: ...") em vez de `password2: ...`.
- Consultas mais eficientes (agregações no banco em vez de laços em Python; cronograma com 1 consulta em vez de 8).
- Metas com prazo vencido passam a "Atrasada".
- Acessibilidade: `aria-expanded` no menu, `role="status"` nas mensagens, rótulos nos botões de ícone.
- Testes automatizados em `core/tests.py`.

## Limpeza
Removidos: pastas `app/` e `sioe_project/` (cópias antigas), arquivos soltos `40`, `60`, `80`, `self.meta_progresso`
(trechos de código criados por engano), `_check.py`, `Logo.png` quebrado, `style.css`/`main.js` sem uso e todos os `__pycache__`.

## Atenção
- `db.sqlite3` e `media/` estão no projeto. Se o repositório for público, **remova do Git** (`git rm --cached`):
  contêm e-mails/senhas (hash) e fotos de usuários.
- O cronograma é uma agenda **semanal recorrente**: a marca de "concluída" vale para todas as semanas.
  Para controlar conclusão por semana seria preciso um novo modelo (ex.: `ConclusaoAtividade(atividade, semana)`).

---

# Segunda rodada

- **Atividades concluídas (Relatórios)** = atividades concluídas no cronograma **+ metas concluídas**.
- **Horas estudadas (Relatórios) e Horas de estudo (Cronograma)** = soma da duração das atividades **concluídas**.
  Novo campo `Atividade.data_conclusao` (preenchido ao concluir, limpo ao reabrir; atividades já concluídas recebem a data de
  criação na migração). Ele alimenta o filtro de período, o gráfico dos últimos 7 dias, a distribuição por matéria e a lista de
  "Concluídas recentemente". O registro manual de estudo foi removido da interface (o model `RegistroEstudo` e seus dados continuam no banco).
- **Matérias nos Relatórios** = matérias cadastradas: ao adicionar uma aparece, ao excluí-la na página Matérias ela some.
- **Cor de destaque (Configurações → Aparência)** agora colore os ícones de todas as páginas e deriva dela os brilhos e gradientes dos botões.
- **Tema "Azul Degradê"**: fundo e sidebar em azul escuro com degradê da cor selecionada.
  (Usa `color-mix()`: navegadores a partir de Chrome 111, Safari 16.2 e Firefox 113.)

# Terceira rodada — cronograma por semana
- Cada atividade agora tem uma **data** e pertence a uma única semana (antes se repetia em todas, inclusive nas passadas).
  Semanas passadas mostram só o que foi registrado nelas; sem registro, ficam vazias.
- Ao criar uma atividade, ela vai para a semana que está sendo exibida (no dia escolhido).
- As estatísticas do Cronograma (atividades, horas concluídas, taxa) passaram a ser da semana exibida.
- Migração `0005_atividade_data`: atividades existentes ficam na semana em que foram criadas.
