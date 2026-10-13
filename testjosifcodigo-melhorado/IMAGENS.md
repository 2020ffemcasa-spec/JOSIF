# 🖼️ Guia de Imagens — SIOE

Como o projeto gera as ilustrações em **SVG** (feitas por código), ele funciona **sem nenhuma imagem externa**.
Abaixo está tudo o que você pode trocar por fotos/imagens reais e exatamente onde colocá-las.

---

## 1. Onde colocar as imagens

Todas as imagens estáticas ficam em:

```
JOSIF-main/
└── static/
    └── core/
        ├── css/
        ├── js/
        └── img/        ← COLOQUE AQUI
```

> Depois de adicionar/substituir um arquivo, se o servidor estiver rodando com
> `runserver` normal (com reload), ele já enxerga. Arquivos novos em `static/`
> também aparecem imediatamente no modo DEBUG.

---

## 2. Slots prontos (é só soltar o arquivo)

| Arquivo a criar | O que aparece | Tamanho sugerido |
|---|---|---|
| `static/core/img/hero-foto.jpg` | **Substitui a ilustração** da tela de Login e de Cadastro (painel esquerdo) | 1200×900 px, JPG/PNG, < 400 KB |
| `static/core/img/logo.svg` | Marca no favicon, sidebar, login, cadastro e "Sobre" | vetorial — pode reescrever |
| `static/core/img/avatar-default.svg` | Avatar de quem ainda não subiu foto | 240×240 px |

**Não precisa mexer em código nenhum** no caso do `hero-foto.jpg`:
o template já está preparado para usá-lo se ele existir e, se não existir,
mantém a ilustração atual automaticamente.

```html
<!-- já está em login.html e cadastro.html -->
<img class="auth-hero" src="{% static 'core/img/hero-foto.jpg' %}" alt=""
     onerror="this.remove()" onload="this.nextElementSibling.style.display='none'">
```

---

## 3. Avatar do usuário (foto de perfil)

Duas formas:

1. **Pela interface**: `Configurações → Perfil → 📷` (fica em `media/avatars/`).
2. **Direto no disco**: jogue o arquivo em `media/avatars/` e associe no admin Django.

Arquivo padrão (sem foto): `static/core/img/avatar-default.svg`.

---

## 4. Ilustrações de "estado vazio" (páginas sem dados)

Cada uma aparece quando o usuário ainda não cadastrou nada:

| Arquivo | Onde aparece |
|---|---|
| `static/core/img/empty-materias.svg` | Matérias (vazio) |
| `static/core/img/empty-agenda.svg` | Dashboard e Cronograma (vazio) |
| `static/core/img/empty-metas.svg` | Dashboard e Metas (vazio) |
| `static/core/img/empty-relatorios.svg` | Relatórios (sem dados) |

Para trocar por uma arte sua: **substitua o arquivo mantendo o mesmo nome e extensão `.svg`**,
ou troque o `src` no template correspondente.

---

## 5. Logotipo

- Atual: `static/core/img/logo.svg` (hexágono com gradiente ciano → violeta).
- O arquivo antigo `static/core/img/Logo.png` (3 bytes) está **quebrado** e **não é mais usado**.
  Pode apagar com segurança.
- Para usar um PNG/JPG no lugar: altere em `core/templates/core/base.html` a linha
  `<link rel="icon" ... href="{% static 'core/img/logo.svg' %}">` e as três ocorrências de
  `core/img/logo.svg`.

---

## 6. Dicas de formato

- **Preferir SVG** para logos, ícones e ilustrações (escala sem perder qualidade).
- **JPG** para fotos (menor tamanho); **PNG** quando precisar de transparência.
- Comprima antes de subir (ex.: [squoosh.app](https://squoosh.app)) — meta de < 300 KB por imagem.
- Nomeie em minúsculas e sem acento: `hero-foto.jpg`, `capa-materias.png`.
