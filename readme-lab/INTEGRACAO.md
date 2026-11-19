# Integrar o laboratório da Shiina

Esta pasta é um caderno navegável em inglês para combinar com o perfil atual. O visitante abre os painéis pelo próprio GitHub. O laboratório contém três experiências em Markdown, com imagens SVG locais e descrições de texto.

## Auditoria do perfil

A leitura de 19 de novembro de 2026 encontrou o arquivo público `README.md` em `main`. A versão do arquivo consultada tem o identificador Git blob `94ae8cdcc69ebc0d1bd49938ef6089d984f41674`. O jogo publica a captura do emulador, o total de comandos aceitos, o último comando e o ranking. O motor e o save são privados. A leitura encontrou **46 comandos comunitários aceitos**. Esse contador alimenta o retrato inicial da sala de saves. A configuração pública descreve o funcionamento do jogo. [README consultado](https://github.com/ravazzoligabriel-commits/ravazzoligabriel-commits/blob/main/README.md) · [Funcionamento do GitBoy](https://github.com/ravazzoligabriel-commits/ravazzoligabriel-commits/blob/main/docs/community-gba.md)

| Bloco existente | Conteúdo que permanece sob seu controle atual |
| --- | --- |
| `COMMUNITY-GBA:START` até `COMMUNITY-GBA:END` | Console, botões, ranking e como jogar |
| `BAD-TAKE:START` até `BAD-TAKE:END` | BAD TAKE no itch.io e GIFs públicos |
| `CURRENTLY-BUILDING:START` até `CURRENTLY-BUILDING:END` | Prévias públicas de Realorant e SIGILO |

O novo caderno entra depois dos blocos existentes. Os destinos do estúdio levam à página de BAD TAKE e aos clipes que o perfil já expõe. A navegação usa títulos, imagens relativas e elementos `details`/`summary` com uma ação por seção. [Sintaxe de Markdown do GitHub](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax) · [Seções recolhíveis](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-collapsed-sections)

## Aplicar em uma branch de trabalho

Mantenha a pasta com o nome `readme-lab` na raiz do repositório do perfil. A prévia do caderno é o `README.md` desta pasta. Na raiz do repositório, os comandos abaixo mostram a diferença local, inserem o caderno e permitem rever a mudança.

```bash
python3 readme-lab/tools/integrate.py README.md
python3 readme-lab/tools/integrate.py README.md --write
git diff -- README.md
```

O primeiro uso anexa o caderno após o conteúdo existente. Nas execuções seguintes, o integrador compara o conteúdo e atualiza apenas o trecho entre `SHIINA-LAB:START` e `SHIINA-LAB:END`. Ele verifica a presença dos três blocos do perfil, a ordem dos seus próprios marcadores e a ausência de sobreposição. Para integração por API, `python3 readme-lab/tools/integrate.py --block` imprime o Markdown já com os caminhos relativos à raiz do repositório. As três salas funcionam dentro do próprio README. Os cliques em **Play** e nos clipes abrem os destinos públicos.

## Atualizar o diário

Edite `readme-lab/data/saves.json` para registrar um save pessoal. `done` aceita os nomes dos objetivos concluídos conforme a lista `goals`. O valor `null` indica que Mashiro ainda não compartilhou um registro. Uma lista vazia `[]` registra zero objetivos concluídos. Por exemplo, `"done": ["Buy a map"]` preenche um dos três segmentos de Hollow Knight.

```bash
python3 readme-lab/tools/render.py
python3 readme-lab/tools/render.py --check
python3 readme-lab/tools/integrate.py README.md --write
```

Para atualizar o contador comunitário, aponte o gerador para uma cópia recente do README público e indique a data em que o perfil foi observado. O valor vem da coluna `COMMUNITY COMMANDS` do bloco `COMMUNITY-GBA`. O gerador grava a data e o Git blob da cópia lida para permitir conferência posterior.

```bash
python3 readme-lab/tools/render.py --profile README.md --as-of AAAA-MM-DD
```

Substitua `AAAA-MM-DD` pela data real da coleta. O contador do painel é um retrato datado e o link de FireRed abre a captura publicada pelo jogo. O diário registra comandos comunitários e objetivos pessoais escolhidos. O progresso interno da ROM, as insígnias e o save compartilhado permanecem sob o fluxo do jogo. A manutenção usa somente Python 3.9 ou posterior e biblioteca padrão.

## Como as três salas foram construídas

| Sala | Interação nativa | Fonte dos dados |
| --- | --- | --- |
| Orbit room | Abrir a vista de cima e a vista rasante, observar Saturno em cada projeção | Oito círculos com fases fixas desenhados em 3D e projetados ortograficamente a 0°, 55° e 78° do eixo vertical. A ordem dos planetas segue o guia da NASA. |
| Studio shelves | Escolher uma intenção e abrir a gaveta correspondente | Jogo da jam no itch.io e clipes do perfil público. Os três emblemas são ilustrações originais. |
| Save room | Abrir o diário comunitário ou o pessoal e consultar seus objetivos | Contador público do FireRed e dois registros editáveis em `data/saves.json`. |

As pranchas SVG incluem título e descrição e usam recursos vetoriais locais. Os textos do Markdown repetem as informações essenciais para leitura em telas pequenas e com leitores de tela. [Guia de planetas da NASA](https://science.nasa.gov/solar-system/planets/)
