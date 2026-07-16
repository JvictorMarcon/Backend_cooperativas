from flask import Flask, jsonify, request
import os
from flask_cors import CORS
from dotenv import load_dotenv
from flasgger import Swagger
from supabase import create_client, Client
from datetime import datetime

# Carregando variáveis de ambiente do arquivo .env
load_dotenv()

url = str(os.getenv("url"))
key = str(os.getenv("key"))

COOPERATIVAS = ["santa maria", "coopersel"]

# Criando o cliente do Supabase
supabase: Client = create_client(url, key)

# Criando o aplicativo
app = Flask(__name__)

CORS(app, origins="*")

swagger = Swagger(app, template_file='openapi.yaml')


# ========================
#   Funções auxiliares
# ========================

# PRIMEIRO: Defina get_cooperativa_id_by_user
def get_cooperativa_id_by_user(user):
    try:
        response = supabase.table("usuarios").select("cooperativa").eq("user", user).execute()
        if response.data:
            coop_val = response.data[0].get("cooperativa")
            if coop_val is not None:
                return int(coop_val)
    except Exception as e:
        print(f"Erro ao buscar cooperativa do usuario {user}: {e}")

    # Fallback dicionario
    usuarios_cooperativas = {
        "vitoria": 1,    # Santa Maria
        "regina": 2,     # Coopersel
    }

    return usuarios_cooperativas.get(user.lower())


def login(user, senha):
    """
    Verifica as credenciais do usuário no banco de dados.
    """
    if not user or not senha:
        return None, None

    try:
        response = supabase.table("usuarios").select(
            "*").eq("user", user).eq("senha", senha).execute()
        usuarios = response.data

        if not usuarios:
            return None, None

        usuario = usuarios[0]
        user_encontrado = usuario.get('user')
        cargo_encontrado = usuario.get('cargo')

        if user_encontrado is None or cargo_encontrado is None:
            return None, None

        return user_encontrado, cargo_encontrado

    except Exception as e:
        print(f"Erro no login: {e}")
        return None, None


def buscar_dados_por_cargo(cargo, user):
    """
    Busca os dados específicos baseado no cargo do usuário.
    """
    try:
        if cargo == 'adm':
            recebimento = supabase.table(
                "recebimento").select("*").order("id", desc=True).execute().data
            triagem = supabase.table("triagem").select("*").order("id", desc=True).execute().data
            prensa = supabase.table("prensa").select("*").order("id", desc=True).execute().data
            bazar = supabase.table("bazar").select("*").order("id", desc=True).execute().data

            return {
                "message": "Dados de todas as cooperativas",
                "cooperativas": "Todas",
                "recebimento": recebimento,
                "triagem": triagem,
                "prensa": prensa,
                "bazar": bazar
            }

        elif cargo == 'tesoureira':
            cooperativa_id = get_cooperativa_id_by_user(user)

            if cooperativa_id is None:
                print(f"Usuário não encontrado no mapeamento ou sem cooperativa: {user}")
                return None

            nome_cooperativa = "Santa Maria" if cooperativa_id == 1 else "Coopersel"

            recebimento = supabase.table("recebimento").select(
                "*").eq("cooperativa_id", cooperativa_id).order("id", desc=True).execute().data
            triagem = supabase.table("triagem").select(
                "*").eq("cooperativa_id", cooperativa_id).order("id", desc=True).execute().data
            prensa = supabase.table("prensa").select(
                "*").eq("cooperativa_id", cooperativa_id).order("id", desc=True).execute().data
            bazar = supabase.table("bazar").select(
                "*").eq("cooperativa_id", cooperativa_id).order("id", desc=True).execute().data

            return {
                "message": f"Dados da cooperativa {nome_cooperativa}",
                "cooperativa": nome_cooperativa,
                "cooperativa_id": cooperativa_id,
                "recebimento": recebimento,
                "triagem": triagem,
                "prensa": prensa,
                "bazar": bazar
            }

        else:
            return None

    except Exception as e:
        print(f"Erro ao buscar dados: {str(e)}")
        return None


# ========================
#   Rotas
# ========================

@app.route('/')
def index():
    return jsonify({
        "message": "Bem-vindo à API de Cooperativas",
        "version": 1.0,
        "author": "João Victor Marcondes"
    }), 200


@app.route('/recebimento', methods=['POST'])
def enviar_recebimento():
    dados = request.get_json()

    if not dados:
        return jsonify({"error": "Nenhum dado fornecido"}), 400

    campos = ["procedencia", "placa_caminhao", "peso_total", 
              "material_tipo", "recebido_por", "cooperativa"]
    if not all(campo in dados for campo in campos):
        return jsonify({"error": "Campos obrigatórios ausentes"}), 400

    procedencia = dados["procedencia"]
    if procedencia not in ["coleta", "mercado"]:
        return jsonify({"error": "Procedência inválida"}), 400

    cooperativa = dados["cooperativa"]
    if cooperativa.lower() not in COOPERATIVAS:
        return jsonify({"error": "Cooperativa inválida"}), 400

    id_cooperativa = 1 if cooperativa.lower() == "santa maria" else 2

    try:
        dados_recebimento = {
            "procedencia": procedencia,
            "placa_caminhao": dados["placa_caminhao"],
            "peso_total": float(dados["peso_total"]),
            "material_tipo": dados["material_tipo"],
            "recebido_por": dados["recebido_por"],
            "cooperativa_id": id_cooperativa
        }

        supabase.table("recebimento").insert(dados_recebimento).execute()

        return jsonify({
            "message": "Dados enviados com sucesso!",
            "horario_envio": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }), 200

    except Exception as e:
        return jsonify({
            "message": "Ocorreu um erro ao cadastrar os dados no banco de dados.",
            "error": str(e)
        }), 400


@app.route('/triagem', methods=['POST'])
def enviar_triagem():
    dados = request.get_json()

    if not dados:
        return jsonify({"error": "Nenhum dado fornecido"}), 400

    campos = ["mesa_id", "material_tipo", "qntd_bags", "peso_rejeito", "cooperativa"]
    if not all(campo in dados for campo in campos):
        return jsonify({"error": "Campos obrigatórios ausentes"}), 400

    cooperativa = dados["cooperativa"]
    if cooperativa.lower() not in COOPERATIVAS:
        return jsonify({"error": "Cooperativa inválida"}), 400

    id_cooperativa = 1 if cooperativa.lower() == "santa maria" else 2

    try:
        dados_triagem = {
            "mesa_id": int(dados["mesa_id"]),
            "material_tipo": dados["material_tipo"],
            "qntd_bags": int(dados["qntd_bags"]),
            "peso_rejeito": float(dados["peso_rejeito"]),
            "cooperativa_id": id_cooperativa
        }

        supabase.table("triagem").insert(dados_triagem).execute()

        return jsonify({"message": "Triagem registrada com sucesso!"}), 200

    except Exception as e:
        return jsonify({
            "message": "Erro ao registrar triagem no banco de dados.",
            "error": str(e)
        }), 400


@app.route('/prensa', methods=['POST'])
def enviar_prensa():
    dados = request.get_json()

    if not dados:
        return jsonify({"error": "Nenhum dado fornecido"}), 400

    campos = ["material_tipo", "qtd_fardos_prensa", "qnt_material_final", "cooperativa"]
    if not all(campo in dados for campo in campos):
        return jsonify({"error": "Campos obrigatórios ausentes"}), 400

    cooperativa = dados["cooperativa"]
    if cooperativa.lower() not in COOPERATIVAS:
        return jsonify({"error": "Cooperativa inválida"}), 400

    id_cooperativa = 1 if cooperativa.lower() == "santa maria" else 2

    try:
        dados_prensa = {
            "material_tipo": dados["material_tipo"],
            "qtd_fardos_prensa": int(dados["qtd_fardos_prensa"]),
            "qnt_material_final": float(dados["qnt_material_final"]),
            "cooperativa_id": id_cooperativa
        }

        supabase.table("prensa").insert(dados_prensa).execute()

        return jsonify({"message": "Dados da prensa registrados com sucesso!"}), 200

    except Exception as e:
        return jsonify({
            "message": "Erro ao registrar prensa no banco de dados.",
            "error": str(e)
        }), 400


@app.route('/bazar', methods=['POST'])
def enviar_bazar():
    dados = request.get_json()

    if not dados:
        return jsonify({"error": "Nenhum dado fornecido"}), 400

    if "valor" not in dados or "entrada" not in dados or "motivo" not in dados or "cooperativa" not in dados:
        return jsonify({"error": "Campos obrigatórios ausentes"}), 400

    cooperativa = dados["cooperativa"]
    if cooperativa.lower() not in COOPERATIVAS:
        return jsonify({"error": "Cooperativa inválida"}), 400

    id_cooperativa = 1 if cooperativa.lower() == "santa maria" else 2

    try:
        dados_bazar = {
            "valor": float(dados["valor"]),
            "entrada": dados["entrada"],
            "motivo": dados["motivo"],
            "cooperativa_id": id_cooperativa
        }

        supabase.table("bazar").insert(dados_bazar).execute()
        return jsonify({"message": "Dados do bazar registrados com sucesso!"}), 200

    except Exception as e:
        return jsonify({
            "message": "Erro ao registrar bazar no banco de dados.",
            "error": str(e)
        }), 400


@app.route('/consultar', methods=['POST'])
def consultar_dados():
    try:
        dados = request.get_json()

        if not dados:
            return jsonify({"error": "Dados não fornecidos"}), 400

        user = dados.get('user')
        senha = dados.get('senha')

        if not user or not senha:
            return jsonify({"error": "Credenciais não fornecidas"}), 400

        user_autenticado, cargo = login(user, senha)

        if not user_autenticado:
            return jsonify({"error": "Credenciais inválidas"}), 401

        if cargo not in ['adm', 'tesoureira']:
            return jsonify({"error": "Acesso negado - Permissão insuficiente"}), 403

        dados_consulta = buscar_dados_por_cargo(cargo, user_autenticado)

        if dados_consulta is None:
            return jsonify({"error": "Erro ao buscar dados"}), 500

        dados_consulta["usuario"] = {
            "nome": user_autenticado,
            "cargo": cargo,
        }

        return jsonify(dados_consulta), 200

    except Exception as e:
        print(f"Erro em consultar_dados: {str(e)}")
        return jsonify({
            "error": "Erro interno no servidor",
            "details": str(e)
        }), 500


@app.route('/login', methods=['POST'])
def verificar_login():
    try:
        dados = request.get_json()

        if not dados:
            return jsonify({"error": "Dados não fornecidos"}), 400

        user = dados.get('user')
        senha = dados.get('senha')

        if not user or not senha:
            return jsonify({"error": "Credenciais não fornecidas"}), 400

        user_autenticado, cargo = login(user, senha)

        if not user_autenticado:
            return jsonify({"error": "Credenciais inválidas"}), 401

        cooperativa_id = get_cooperativa_id_by_user(user_autenticado)
        cooperativa_nome = None
        if cooperativa_id == 1:
            cooperativa_nome = "santa maria"
        elif cooperativa_id == 2:
            cooperativa_nome = "coopersel"

        return jsonify({
            "usuario": user_autenticado,
            "cargo": cargo,
            "cooperativa": cooperativa_nome,
            "cooperativa_id": cooperativa_id,
            "autenticado": True
        }), 200

    except Exception as e:
        print(f"Erro em verificar_login: {str(e)}")
        return jsonify({
            "error": "Erro interno no servidor",
            "details": str(e)
        }), 500


@app.route('/consultar/filtrado', methods=['POST'])
def consultar_dados_filtrados():
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({"error": "Dados não fornecidos"}), 400
            
        user = dados.get('user')
        senha = dados.get('senha')
        tabela = dados.get('tabela')
        filtros = dados.get('filtros', {})
        
        # Autenticação
        user_autenticado, cargo = login(user, senha)
        if not user_autenticado:
            return jsonify({"error": "Credenciais inválidas"}), 401
        
        if cargo not in ['adm', 'tesoureira']:
            return jsonify({"error": "Acesso negado"}), 403
        
        # Valida tabela
        if tabela not in ['recebimento', 'triagem', 'prensa', 'bazar']:
            return jsonify({"error": "Tabela inválida"}), 400
        
        # Constrói query base
        query = supabase.table(tabela).select("*")
        
        # Filtro de cooperativa (obrigatório para tesoureira)
        if cargo == 'tesoureira':
            cooperativa_id = get_cooperativa_id_by_user(user_autenticado)
            if cooperativa_id is None:
                return jsonify({"error": "Usuário não vinculado a cooperativa"}), 400
            query = query.eq("cooperativa_id", cooperativa_id)
        
        # Aplica filtros dinâmicos
        for chave, valor in filtros.items():
            # ✅ CORRIGIDO: Filtros de data
            if chave == 'data_inicio':
                query = query.gte("data_criacao", valor)
            elif chave == 'data_fim':
                query = query.lte("data_criacao", valor)
            # Filtros de peso
            elif chave == 'peso_minimo':
                query = query.gte("peso_total", float(valor))
            elif chave == 'peso_maximo':
                query = query.lte("peso_total", float(valor))
            # ✅ CORRIGIDO: Filtros de texto
            elif chave == 'busca_texto':
                # Supabase OR syntax
                query = query.or_(f"material_tipo.ilike.%{valor}%,procedencia.ilike.%{valor}%")
            # Filtros exatos
            else:
                query = query.eq(chave, valor)
        
        # Ordenação
        if 'ordenar_por' in filtros:
            ordem = filtros.get('ordenar_por')
            direcao = filtros.get('ordem_direcao', 'asc')
            if direcao == 'desc':
                query = query.order(ordem, desc=True)
            else:
                query = query.order(ordem)
        
        # Limite e paginação
        if 'limite' in filtros:
            query = query.limit(int(filtros['limite']))
        if 'offset' in filtros:
            query = query.offset(int(filtros['offset']))
        
        # Executa consulta
        resultado = query.execute()
        
        return jsonify({
            "tabela": tabela,
            "filtros_aplicados": filtros,
            "total": len(resultado.data),
            "dados": resultado.data
            
        }), 200
        
    except Exception as e:
        print(f"Erro: {str(e)}")
        return jsonify({"error": str(e)}), 500


# =====================================
#     Rotas de tratamento de erros
# =====================================
@app.errorhandler(404)
def erro404(error):
    return jsonify({"error": "URL não encontrada"}), 404


@app.errorhandler(500)
def erro500(error):
    return jsonify({"error": "Servidor interno com falhas. Tente mais tarde"}), 500


if __name__ == "__main__":
    app.run(debug=True)