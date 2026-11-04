# Plano de ação — Parte 2: serviço de alerta na AWS

Plano para executar a Parte 2 do enunciado. O código inicial está em `servicos/fase7-alertas-aws/`. A dashboard da Fase 4 e a branch `master` não entram nesta entrega.

Trabalho local na branch `feature/alertas-aws-edemir`. Nada foi enviado ao remoto. Na hora de enviar, o push sai desta branch, nunca da `master` ou da `main`.

## O que o enunciado pede

1. Criar o serviço na infraestrutura da Fase 5: EC2 Linux `t3.micro`, EBS `gp3` de 50 GB, região São Paulo (`sa-east-1`).
2. Um serviço de mensageria na AWS monitora uma fonte. A fonte desta entrega é a previsão da Fase 2, já exposta por `farmtech_integracao.fase2.forecast`.
3. Enviar e-mail ao funcionário com o alerta e a ação corretiva. SMS não faz parte deste corte.

## Regras do grupo

Cultura: tomate, com os limiares já gravados no firmware da Fase 2.

| Condição na janela de 12 horas | Alerta | Ação corretiva |
|---|---|---|
| Alguma hora com chuva de 1 mm ou mais | Chuva prevista | Manter a bomba desligada |
| Sem essa chuva, e umidade abaixo de 45% | Umidade baixa | Ligar a irrigação do tomate |
| Sem os dois casos acima, e umidade acima de 80% | Umidade alta | Manter a bomba desligada |
| Nenhum limiar cruzado | Sem aviso | O serviço não publica |

A chuva vem antes da umidade baixa, para não pedir irrigação debaixo de chuva. pH e NPK continuam no firmware; a previsão Open-Meteo não traz esses campos, então o e-mail não inventa valores deles.

## Passo a passo

### 1. Conferir o aviso sem AWS

Na raiz do repositório, com o Python 3.11.9 da Fase 4:

```powershell
python servicos/fase7-alertas-aws/monitorar.py --cidade "Irecê"
```

O comando consulta a Fase 2, aplica a regra e imprime o e-mail. Sem `--enviar`, nada é publicado.

Teste das regras, sem rede:

```powershell
python -m unittest servicos/fase7-alertas-aws/test_regras.py -v
```

### 2. Montar a EC2 da Fase 5

No console da AWS Academy ou no Learner Lab, região **América do Sul (São Paulo) / sa-east-1**:

- AMI Amazon Linux.
- Instância `t3.micro`.
- Volume EBS `gp3` de 50 GB.
- Security group com SSH apenas do IP de quem opera. A instância não publica site.

Antes de criar, incluir esta EC2 e o Amazon SNS na calculadora da AWS (`https://calculator.aws`), na mesma região. A estimativa da Fase 5, US$ 19,86 por mês, cobre só a EC2 e o EBS. O tópico de e-mail entra à parte.

### 3. Mensageria

Ainda em `sa-east-1`:

1. Criar o tópico padrão `farmtech-alertas-funcionarios`.
2. Criar uma assinatura **e-mail** com o endereço do grupo.
3. Abrir o e-mail da AWS e confirmar a assinatura. Sem essa confirmação o aviso não chega.
4. Copiar o ARN do tópico. Ele entra só no ambiente da instância, no formato `arn:aws:sns:sa-east-1:CONTA:farmtech-alertas-funcionarios`.

### 4. Permissão mínima

Criar uma função IAM para a EC2 com esta política, trocando a conta e o nome se forem diferentes:

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

Associar a função à instância. Não criar chave de acesso no repositório e não gravar senha em arquivo versionado.

### 5. Colocar o monitor na instância

Copiar para a EC2 a pasta `servicos/fase7-alertas-aws/`, o pacote `farmtech_integracao/` e `servicos/fase2-iot/scripts/weather_forecast.py`, preservando esses caminhos relativos. Instalar somente:

```bash
pip install -r servicos/fase7-alertas-aws/requirements.txt
```

Variáveis na instância:

```bash
AWS_DEFAULT_REGION=sa-east-1
AWS_SNS_TOPIC_ARN=arn:aws:sns:sa-east-1:CONTA:farmtech-alertas-funcionarios
```

Publicar de verdade, uma vez, para a evidência:

```bash
python servicos/fase7-alertas-aws/monitorar.py --cidade "Irecê" --enviar
```

`--enviar` publica só quando existe alerta. Se a previsão estiver dentro da faixa, o comando avisa que não houve publicação.

Agendar na EC2, a cada hora, o mesmo comando com `--enviar`. Se o mesmo tipo de alerta já foi publicado nas últimas 6 horas, o script recusa uma segunda publicação. O registro fica em `servicos/fase7-alertas-aws/.ultimo-alerta.json`, fora do Git.

### 6. Evidência da entrega

Guardar:

- a região e o tipo da instância (`t3.micro`, `sa-east-1`, volume de 50 GB);
- o tópico SNS e a assinatura de e-mail confirmada;
- a saída do monitor com cidade, umidade ou chuva e a ação;
- o e-mail recebido, com alerta e ação corretiva.

Ao terminar, parar a instância. O capítulo 13 avisa que o recurso continua existindo depois do período gratuito e pode gerar cobrança.

## O que fica de fora

- Dashboard, páginas Streamlit e a branch `master`.
- Fase 6 e o ambiente Python 3.13.
- SMS.
- Push para o remoto, até o grupo decidir enviar a branch `feature/alertas-aws-edemir`.
