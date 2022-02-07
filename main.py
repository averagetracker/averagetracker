from flask import Flask, render_template, url_for, request
#-----------------------
import locale
import os
import sys

from rich import print
from rich.console import Console
from rich.table import Table
import inquirer

from requests import request as req
import math
#------------------------------


app = Flask(__name__)

 

@app.route('/')
@app.route('/home')
def home():
    return render_template("index.html")





@app.route('/result',methods=['POST', 'GET'])
def result():
    output = request.form.to_dict()
    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
    console = Console()
    username = output["username"]
    password = output["password"]

    print("Connexion...")
    payload = 'data={ "identifiant": "' + username + \
              '", "motdepasse": "' + password + '", "acceptationCharte": true }'
    try:
        response = req(
            "POST", "https://api.ecoledirecte.com/v3/login.awp", data=payload).json()
        token = response['token'] or token
        loginRes = response
    except Exception as exception:
        if type(exception).__name__ == "ConnectionError":
            print("[reverse bold red]La connexion a échoué[/]")
            print("[red]Vérifiez votre connexion Internet.[/]")
        else:
            print("[reverse bold red]Une erreur inconnue est survenue.[/]")
        console.input(password=True)
        exit()
    if not token:
        print(loginRes['message'])
        console.input(password=True)
        exit()
        
    # Sélectionne ou demande le compte à retourner
    # Filtre les comptes de type E
    e_accounts = list(filter(lambda account: bool(
        account['typeCompte'] == "E"), loginRes['data']['accounts']))
    # Met en page les choix
    choices = list(
        map(lambda account: (str(account['id']) + " | " + account['prenom'] + " " + account['nom']),
            e_accounts))
    # Choix automatique
    choice = None
    if len(choices) > 1:
        choice = choose("Sélectionnez un compte disponible: ", choices=choices)
    elif len(choices) < 1:
        choice = None
    elif len(choices) == 1:
        choice = choices[0]
    if not choice:
        # Pas de compte supporté
        print("[reverse bold red]Aucun compte compatible trouvé[/]")
        print("[red]Essayez de vous connecter avec un compte Elève.[/]")
        console.input(password=True)
        exit()

    account = next(filter(lambda account: (
        str(account['id']) == choice[0:4]), e_accounts), None)
    if not account:
        # Aucun compte supporté
        print("[reverse bold red]Aucun compte compatible trouvé[/]")
        print("[red]Essayez de vous connecter avec un compte Elève.[/]")
        console.input(password=True)
        exit()

    print(f"[blue]Bonjour, [bold]{account['prenom']}[/].[/]")
    name = account['prenom']
    print("Collecte des notes...")

    payload = 'data={"token": "' + token + '"}'
    response = req("POST", "https://api.ecoledirecte.com/v3/eleves/" +
                   str(account['id']) + "/notes.awp?verbe=get&", data=payload).json()
    token = response['token'] or token
    notesRes = response

    if notesRes['code'] != 200:
        print(notesRes['message'])
        console.input(password=True)
        exit()
    print("Traitement des notes...")

    # Affiche la moyenne pour chaque période (et chaque matière)
    periodes = notesRes['data']['periodes']
    notes = notesRes['data']['notes']

    for periode in periodes:
        matieres = periode['ensembleMatieres']['disciplines']
        notes_list = []  # Liste des notes (=> calcul de la médiane)
        notes_periode = 0  # Somme des notes de la période
        diviseur_periode = 0  # Somme des coefficients
        infos_matieres = {}
        missing_subject_weight = False

        for matiere in matieres:
            notes_list_matiere = []
            notes_matiere = 0
            diviseur_matiere = 0
            coef_matiere = float(matiere['coef']) or 1
            if not float(matiere['coef']):
                missing_subject_weight = True
            notesM = list(filter(lambda note: (note['codePeriode'] == periode['idPeriode']) and
                                              (note['codeMatiere'] == matiere['codeMatiere']), notes))
            for note in notesM:
                try:
                    if not note["nonSignificatif"]:
                        notes_matiere += (locale.atof(note['valeur']) / locale.atof(note['noteSur'])) * \
                            locale.atof(note['coef'])
                        diviseur_matiere += locale.atof(note['coef'])
                        notes_list.append(locale.atof(
                            note['valeur']) / locale.atof(note['noteSur']))
                        notes_list_matiere.append(locale.atof(
                            note['valeur']) / locale.atof(note['noteSur']))
                except:
                    pass

            moyenne_matiere = None
            notes_list_matiere.sort()

            if diviseur_matiere:
                moyenne_matiere = (notes_matiere / diviseur_matiere)
                notes_periode += moyenne_matiere * coef_matiere
                diviseur_periode += coef_matiere
            infos_matieres[matiere['codeMatiere']] = {
                'moyenne': moyenne_matiere if diviseur_matiere else None,
                'mediane': notes_list_matiere[round((len(notes_list_matiere) - 1) / 2)] if notes_list_matiere else None,
                'rang': matiere['rang'],
                'coef': coef_matiere
            }

        notes_list.sort()

        if diviseur_periode:
            # Création du tableau
            table = Table(title=periode['periode'])
            table.add_column("Matière", style='cyan', justify='left')
            table.add_column("Coef", style='white', justify='center')
            table.add_column("Moyenne", style='magenta', justify='center')
            table.add_column("Médiane", style='hot_pink', justify='center')
            table.add_column("Rang", style='green', justify='right')

            for codeMatiere in infos_matieres:
                matiere = infos_matieres[codeMatiere]
    #======================================
                print(codeMatiere)
                print("coef: ")
                print(matiere["coef"])

    #           moyenne de chaques moyennes
                print("moyenne: ")
                if matiere["moyenne"] != None:
                    moyenne_liste = (str(round(matiere['moyenne'] * 20, 2)))
                else:
                    print("None")

    #           médiane
                print("médiane: ")
                if matiere["mediane"] != None:
                    print(str(round(matiere['mediane'] * 20, 2)))
                else:
                    print("None")
    #======================================
                if codeMatiere:
                    table.add_row(codeMatiere, str(matiere['coef']),
                                  str(round(
                                      matiere['moyenne'] * 20, 1) if matiere['moyenne'] else None).zfill(4),
                                  str(round(
                                      matiere['mediane'] * 20, 1) if matiere['mediane'] else None).zfill(4),
                                  f"#{str(matiere['rang']).zfill(2)}")
            moyenne_periode = notes_periode / diviseur_periode
            table.add_row("GENERAL", "0", str(round(moyenne_periode * 20, 1)),
                          str(round((notes_list[round((len(notes_list) - 1) / 2)]) * 20, 1)), "#00", style='red')
            console.print(table)
            moyenne = round(moyenne_periode * 20, 2)
            if missing_subject_weight:
                print("Certaines matières de cette période n'avaient pas de coefficient. La moyenne générale générée est donc probablement erronée.")
            print()


            

    print("Terminé")


    return render_template('result.html', name = name, username = username, password = password, moyenne = moyenne, matiere = matiere)





if __name__ == "__main__":
    app.run(debug=True)