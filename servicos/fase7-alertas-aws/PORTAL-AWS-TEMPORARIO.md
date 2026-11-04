# Portal AWS — do zero até o teste do e-mail

Arquivo auxiliar e temporário. Apague antes da entrega final. O plano da disciplina continua em `PLANO-ACAO-ALERTAS-AWS.md`, na raiz.

Tudo abaixo é na região **América do Sul (São Paulo)**, código `sa-east-1`. Se o seletor de região estiver em outro lugar, o tópico e a instância nascem no lugar errado e o monitor recusa o envio.

A infraestrutura é a da Fase 5: uma EC2 Linux `t3.micro` com disco `gp3` de 50 GB. O aviso sai por e-mail no tópico SNS `farmtech-alertas-funcionarios`.

## 1. Abrir o console

1. Entre no AWS Academy e abra o Learner Lab da disciplina.
2. Clique em **Start Lab** e espere o estado ficar verde.
3. Abra o console pelo botão **AWS**.
4. No canto superior direito, troque a região para **South America (São Paulo) / sa-east-1**.
5. Confira o seletor de novo antes de cada criação. Um recurso criado em N. Virginia não serve.

Se São Paulo não aparecer na lista do laboratório, pare e registre o print. Não mude em silêncio para a Virgínia: a Fase 5 escolheu São Paulo.

## 2. Criar o tópico de e-mail

1. Na busca do console, abra **Simple Notification Service**.
2. No menu esquerdo, **Topics** → **Create topic**.
3. Type: **Standard**.
4. Name: `farmtech-alertas-funcionarios`.
5. Deixe o resto no padrão e clique em **Create topic**.
6. Na página do tópico, copie o **ARN**. Ele tem esta cara:

```text
arn:aws:sns:sa-east-1:123456789012:farmtech-alertas-funcionarios
```

O trecho `sa-east-1` precisa estar no ARN. Guarde esse valor fora do Git.

## 3. Inscrever o e-mail do funcionário

1. Ainda na página do tópico, **Create subscription**.
2. Protocol: **Email**.
3. Endpoint: o e-mail que vai receber o aviso.
4. **Create subscription**. O status fica **Pending confirmation**.
5. Abra a caixa de entrada. O remetente é `no-reply@sns.amazonaws.com`.
6. Abra a mensagem e clique em **Confirm subscription**.
7. Volte em **Subscriptions** e atualize a página. O status tem de estar **Confirmed**.

Sem essa confirmação, o teste seguinte não entrega nada. Olhe também o spam.

## 4. Testar o e-mail pelo portal, antes da instância

Este teste prova a mensageria sem usar o código.

1. Abra o tópico `farmtech-alertas-funcionarios`.
2. **Publish message**.
3. Subject: `FarmTech: teste do portal`.
4. Message body, com o mesmo tipo de texto que o monitor envia:

```text
FarmTech Solutions — aviso aos funcionários

Local: Irecê, Bahia, Brasil
Alerta: Umidade prevista abaixo de 45% para o tomate.
Umidade prevista: 40.0%
Ação corretiva: Ligar a irrigação do tomate.
```

5. **Publish message**.
6. O e-mail inscrito deve chegar em poucos minutos, com esse assunto e essa ação.

Guarde o print do tópico, da assinatura confirmada e do e-mail recebido.

Se não chegar: a região do tópico não é `sa-east-1`, a assinatura ainda está pendente, ou o lab expirou. Não avance para a EC2 enquanto este e-mail não existir.

## 5. Criar a instância da Fase 5

1. Busque **EC2** → **Launch instance**.
2. Name: `farmtech-alertas`.
3. AMI: **Amazon Linux 2023**, 64-bit (x86).
4. Instance type: **t3.micro**. Não aceite o tipo que vier pré-selecionado se for outro.
5. Key pair: **Create new key pair**. Nome `farmtech-alertas`. Tipo RSA, formato `.pem`. Baixe o arquivo e não o coloque no repositório.
6. Network settings: **Create security group**. Marque **Allow SSH traffic from My IP**. Não abra HTTP nem HTTPS. A instância não hospeda a dashboard.
7. Storage: edite o volume raiz. Tamanho **50 GiB**, tipo **gp3**. O padrão da AWS vem com 8 GiB; se não editar, a instância não corresponde à Fase 5.
8. **Launch instance**.
9. Em **Instances**, espere **Running** e **Status check: 2/2 passed**. Copie o **Public IPv4 address**.

## 6. Permissão para publicar

Caminho preferido, se o laboratório deixar criar função:

1. Busque **IAM** → **Roles** → **Create role**.
2. Trusted entity: **AWS service**. Use case: **EC2**. Next.
3. **Create policy**, aba JSON, cole o texto abaixo trocando `CONTA` pelos doze dígitos da conta, visíveis no ARN do tópico:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:sa-east-1:CONTA:farmtech-alertas-funcionarios"
    }
  ]
}
```

4. Nome da política: `farmtech-sns-publish`. Nome da função: `farmtech-ec2-alertas`.
5. EC2 → instância `farmtech-alertas` → **Actions** → **Security** → **Modify IAM role**. Escolha `farmtech-ec2-alertas` e salve.

Se o Learner Lab bloquear a criação de função, use as credenciais temporárias mostradas em **AWS Details** só dentro da instância, no passo 8. Elas morrem quando o lab acaba. Não grave essas chaves no projeto.

## 7. Entrar na instância e levar o código

No PowerShell, a partir da pasta onde está o `.pem`:

```powershell
ssh -i .\farmtech-alertas.pem ec2-user@IP_PUBLICO
```

Saia com `exit`. Na raiz do repositório local, envie só o que o monitor importa:

```powershell
ssh -i .\farmtech-alertas.pem ec2-user@IP_PUBLICO "mkdir -p /home/ec2-user/farmtech/servicos/fase2-iot/scripts /home/ec2-user/farmtech/servicos/fase7-alertas-aws"

scp -i .\farmtech-alertas.pem -r .\farmtech_integracao ec2-user@IP_PUBLICO:/home/ec2-user/farmtech/
scp -i .\farmtech-alertas.pem -r .\servicos\fase7-alertas-aws\* ec2-user@IP_PUBLICO:/home/ec2-user/farmtech/servicos/fase7-alertas-aws/
scp -i .\farmtech-alertas.pem .\servicos\fase2-iot\scripts\weather_forecast.py ec2-user@IP_PUBLICO:/home/ec2-user/farmtech/servicos/fase2-iot/scripts/
```

Entre de novo por SSH.

## 8. Preparar o Python na instância

```bash
cd /home/ec2-user/farmtech
sudo dnf install -y python3 python3-pip
python3 -m pip install --user -r servicos/fase7-alertas-aws/requirements.txt
export AWS_DEFAULT_REGION=sa-east-1
export AWS_SNS_TOPIC_ARN=arn:aws:sns:sa-east-1:CONTA:farmtech-alertas-funcionarios
```

Troque o ARN pelo valor copiado no passo 2. Se a função IAM não pôde ser anexada, rode também `aws configure` e informe a chave, o segredo, a região `sa-east-1` e o session token do **AWS Details**.

## 9. Testes, nesta ordem

Na instância, ainda em `/home/ec2-user/farmtech`.

Teste das regras, sem rede e sem e-mail:

```bash
python3 -m unittest servicos/fase7-alertas-aws/test_regras.py -v
```

Os 8 testes precisam passar.

Teste da previsão real, ainda sem publicar:

```bash
python3 servicos/fase7-alertas-aws/monitorar.py --cidade "Irecê"
```

A saída mostra o e-mail ou a frase `Sem alerta`. As duas são válidas. Esta execução não envia mensagem.

Teste de publicação pelo código. A previsão ao vivo pode estar na faixa normal e, nesse caso, `--enviar` não publica. Para forçar um aviso de umidade baixa, gere um JSON com horário uma hora à frente:

```bash
python3 - <<'PY'
import json
from datetime import datetime, timedelta, timezone
instante = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
json.dump({
    "status": "ok",
    "message": "teste de portal",
    "data": {
        "location": {"name": "Irecê", "admin1": "Bahia", "country": "Brasil"},
        "hourly": [{"ts_iso": instante, "umidade": 40, "rain_mm": 0}],
    },
    "source": {},
}, open("/tmp/alerta-teste.json", "w", encoding="utf-8"), ensure_ascii=False)
PY
python3 servicos/fase7-alertas-aws/monitorar.py --arquivo /tmp/alerta-teste.json --enviar
```

O que confirma o sucesso:

- o terminal imprime `Publicado no SNS. MessageId: ...`;
- o mesmo e-mail inscrito recebe o alerta **Umidade prevista abaixo de 45%** e a ação **Ligar a irrigação do tomate**.

Uma segunda execução igual, em menos de 6 horas, responde que a publicação foi recusada. Isso é a trava de repetição, não uma falha do SNS.

Se aparecer `Defina AWS_SNS_TOPIC_ARN` ou `O tópico precisa estar na região sa-east-1`, o ambiente da instância está incompleto ou o ARN é de outra região. Se aparecer falha ao publicar, a função IAM ou as credenciais do lab não têm `sns:Publish` nesse tópico.

## 10. Encerrar

1. EC2 → instância `farmtech-alertas` → **Stop instance**. Parar interrompe a cobrança de computação. O disco de 50 GB continua existindo.
2. No Learner Lab, **End Lab** quando a evidência estiver salva.
3. Não deixe o lab ligado sem necessidade. O capítulo 13 avisa que o recurso sobrevive ao período de teste e pode gerar custo.

## Evidência mínima

- Região `sa-east-1`, tipo `t3.micro` e volume `gp3` de 50 GB.
- Tópico, assinatura **Confirmed** e o primeiro e-mail publicado pelo portal.
- Saída do `unittest` e a saída do `--enviar` com `MessageId`.
- E-mail recebido a partir do monitor, com alerta e ação corretiva.
