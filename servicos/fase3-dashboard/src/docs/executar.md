# Como Executar o Projeto

## Pré-requisito: instância Oracle da FIAP acessível

O projeto **não usa mais Oracle XE local** (`localhost/XEPDB1`). A base de dados é a **instância institucional da FIAP** — `oracle.fiap.com.br/ORCL`. Confirme **antes de tudo** que:

1. A **VPN/rede FIAP** está disponível (necessária fora do laboratório).
2. O **utilizador `RM…`** e a **senha** fornecidos pela FIAP estão à mão.
3. O DNS resolve `oracle.fiap.com.br` (`ping oracle.fiap.com.br` ou `Test-NetConnection oracle.fiap.com.br -Port 1521` no PowerShell).

> Conexão de exemplo via SQL\*Plus / SQLcl:
> ```bash
> sqlplus RM571375@oracle.fiap.com.br:1521/ORCL
> ```
> Para não deixar a senha no histórico do terminal ou na lista de processos, informe-a apenas quando o SQL*Plus solicitar.

---

## 1. Ativar o ambiente virtual

Na **raiz do módulo** (onde estão `run.py`, `requirements.txt` e `.env`):

```powershell
Set-Location "$HOME\Desktop\farmtech-integracao\servicos\fase3-dashboard"
.venv\Scripts\Activate.ps1
```

> Se o ambiente virtual ainda não existir:
> ```powershell
> python -m venv .venv
> .venv\Scripts\Activate.ps1
> python -m pip install --upgrade pip
> pip install -r requirements.txt
> ```

---

## 2. Configurar credenciais FIAP

Copie `config/.env.example` para `.env` na raiz e preencha com a sua matrícula/senha e o DSN da FIAP:

```env
# .env (raiz do projeto — NUNCA commite)
ORACLE_USER=RM571375
ORACLE_PASS=sua_senha_fiap
ORACLE_DSN=oracle.fiap.com.br:1521/ORCL
```

> Formato alternativo aceito (DSN longo, útil quando o serviço exige `SID`):
> ```env
> ORACLE_DSN=(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=oracle.fiap.com.br)(PORT=1521))(CONNECT_DATA=(SID=ORCL)))
> ```

---

## 3. Testar a conexão Oracle (FIAP)

Antes de subir a API, valide as credenciais com o script auxiliar:

```powershell
python scripts\test_connection.py
```

Saída esperada (resumida):
```
[INFO] DSN: oracle.fiap.com.br:1521/ORCL | Usuário: RM571375
[OK] Conexão estabelecida.
```

Se falhar: rever VPN, `ORACLE_*` no `.env` e horário de manutenção do serviço FIAP.

---

## 4. Arranque integrado — API + Dashboard num único comando (recomendado)

Na raiz, com `.env` preenchido e `.venv` ativo:

```powershell
python run.py
```

O `run.py` orquestra **uvicorn (FastAPI)** + **Streamlit** em paralelo. Ao subir, automaticamente:

- Cadastra **Pato Branco — PR** no Oracle FIAP (se ainda não existir).
- Faz a **primeira coleta** Open-Meteo imediatamente.
- Agenda coletas **a cada 5 minutos** enquanto o processo estiver vivo.

Endpoints e UI:
- **Swagger:** http://localhost:8000/docs
- **Dashboard Streamlit:** http://localhost:8501

Opções úteis:
```powershell
python run.py --api-port 8000 --streamlit-port 8501   # portas customizadas
python run.py --api-reload                            # auto-reload da API (dev)
```

> **Páginas disponíveis no dashboard** (menu lateral):
>
> - **Entrega — Sensores IoT**
> - **Ir além — Painel IA · soluções** (irrigação `bomba_fw` + culturas + **Recomendador inteligente**)
> - **Ir além — Previsão do Tempo**
> - **Ir além — Análise para IA (meteorologia)**
> - **Ir além — Notebook ML**
> - **Ir além — Exportar relatório PDF**

---

## 4-alternativo. Rodar API e dashboard em terminais separados (opcional)

Útil para depuração isolada. Em **dois terminais** distintos, ambos com `.venv` ativo na raiz:

```powershell
# Terminal 1 — API
python run.py --api-only --api-reload
```

```powershell
# Terminal 2 — Dashboard
python run.py --dashboard-only
```

---

## 5. Verificar se tudo está funcionando

Com a API no ar, verifique a saúde do serviço:

```
GET http://localhost:8000/admin/health
```

Resposta esperada:
```json
{
  "status": "ok",
  "scheduler_running": true,
  "next_collection": "2026-05-06 00:30:00 BRT",
  "db_ok": true
}
```

`db_ok: true` confirma que o utilizador FIAP conseguiu abrir conexão com `oracle.fiap.com.br/ORCL`.

---

## Resumo dos processos

| Processo | Comando recomendado | Porta | Função |
|----------|---------------------|-------|--------|
| **API + Dashboard** (integrado) | `python run.py` | 8000 + 8501 | FastAPI (coleta + endpoints) e Streamlit em simultâneo |
| API isolada (opcional) | `python run.py --api-only --api-reload` | 8000 | Apenas FastAPI |
| Dashboard isolado (opcional) | `python run.py --dashboard-only` | 8501 | Apenas Streamlit |

> O modo recomendado é **`python run.py`** — gere os dois processos numa só árvore e encerra ambos com **Ctrl+C**.
> A API é responsável por **coletar e gravar** dados na instância Oracle FIAP; o dashboard apenas **lê** o que já está no banco.

---

## Resolução rápida

| Sintoma | Verificação |
|---------|-------------|
| `ORA-12541: TNS:no listener` ou timeout em `oracle.fiap.com.br` | VPN FIAP ativa? `Test-NetConnection oracle.fiap.com.br -Port 1521`. |
| `ORA-01017: invalid username/password` | Reconfirme `ORACLE_USER`/`ORACLE_PASS` no `.env` (matrícula em maiúsculas: `RM571375`). |
| `db_ok: false` no `/admin/health` | Rodar `python scripts\test_connection.py` para isolar erro de conexão. |
| Portas 8000/8501 ocupadas | `python run.py --api-port 9000 --streamlit-port 9501`. |
| `ModuleNotFoundError` ao subir | Reinstalar dependências: `pip install -r requirements.txt`. |
