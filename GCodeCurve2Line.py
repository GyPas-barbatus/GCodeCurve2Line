import tkinter as tk
from tkinter import filedialog, messagebox
import os
import re
import numpy as np

"""
Cette fonction permet de segmentiser les commandes G2 et G3 pour n'avoir que des commandes G1
"""

def param_standart() :
    dictio_param = {}
    dictio_param['lg_seg'] = 0.2
    return dictio_param
    

def main(param_standard=False,path = None, path_output = None) :


    if path == None :
        path = selection_gcode()
        #path = r'C:\Users\hugue\OneDrive\Bureau\NONAME_0.nc'
    if path_output == None :
        path_output = modify_filename(path, suffix="_segment")

    if param_standard :
        dictio_param = param_standart()
        lg_seg = dictio_param['lg_seg']
    else :    
        lg_seg = interface()

    G1 = False
    G2 = False
    G3 = False
    G17 = True #Par défaut activé
    G18 = False
    G19 = False
    X_ligne = None
    Y_ligne = None
    Z_ligne = None
    I_ligne = None
    J_ligne = None
    X_ligne_old = None
    Y_ligne_old = None
    Z_ligne_old = None

    with open(path, 'r') as fichier,open(path_output, 'w') as fichier_output:
        for ligne in fichier:

            #Plan de rotation
            #Standard (G17) : X,Y
            #G18 : X,Z
            #G19 : Y,Z

            if "G18" in ligne :
                G17 = False
                G18 = True
                G19 = False
            elif "G19" in ligne :
                G17 = False
                G18 = False
                G19 = True
            elif "G17" in ligne :
                G17 = True
                G18 = False
                G19 = False



            #Si on entre dans un bloc G2 ou G3
            if "G2" in ligne :
                G2 = True
            elif "G3" in ligne :
                G3 = True
            elif "G1" in ligne :
                G1 = True
            #Ou si on en sort
            elif "G" in ligne :
                G1 = False
                G2 = False
                G3 = False
                

            if X_ligne is not None :
                X_ligne_old = X_ligne
            if Y_ligne is not None :
                Y_ligne_old = Y_ligne
            if Z_ligne is not None :
                Z_ligne_old = Z_ligne
            #Acquiert les coordonnées de la ligne
            coord = coordonnees_ligne(ligne)
            X_ligne = coord.get("X",None)
            Y_ligne = coord.get("Y",None)
            Z_ligne = coord.get("Z",None)
            I_ligne = coord.get("I",None)
            J_ligne = coord.get("J",None)
            S_ligne = coord.get("S",None)
            F_ligne = coord.get("F",None)

            if G2 or G3 :
                #Si on a un cercle :
                if I_ligne != None and J_ligne != None :
                    #On rend anonyme les coorodonnées pour s'affranchir du plan de rotation
                    if G18 :
                        C_ligne_1_old = X_ligne_old
                        C_ligne_1 = X_ligne
                        C_ligne_2_old = Z_ligne_old
                        C_ligne_2 = Z_ligne
                    elif G19 :
                        C_ligne_1_old = Y_ligne_old
                        C_ligne_1 = Y_ligne
                        C_ligne_2_old = Z_ligne_old
                        C_ligne_2 = Z_ligne
                    else :
                        C_ligne_1_old = X_ligne_old
                        C_ligne_1 = X_ligne
                        C_ligne_2_old = Y_ligne_old
                        C_ligne_2 = Y_ligne

                    #Centre en coordonnées absolues
                    I_abs = I_ligne + C_ligne_1_old
                    J_abs = J_ligne + C_ligne_2_old

                        
                    #Angle de départ
                    dx_dep = C_ligne_1_old - I_abs
                    dy_dep = C_ligne_2_old - J_abs
                    angle_dep = np.arctan2(dy_dep,dx_dep)
                    #Angle d'arrivé
                    dx_arr = C_ligne_1 - I_abs
                    dy_arr = C_ligne_2 - J_abs
                    angle_arr = np.arctan2(dy_arr,dx_arr)

                    #Pas (1 point pour 2/10mm)
                    rayon = np.sqrt((I_ligne)**2+(J_ligne)**2)

                    # Normaliser entre [0, 2π)
                    angle_dep = (angle_dep + 2*np.pi) % (2*np.pi)
                    angle_arr = (angle_arr + 2*np.pi) % (2*np.pi)

                    # Cas spécial : cercle complet
                    if np.isclose(angle_dep, angle_arr, atol=1e-9):
                        if G3:  # anti-horaire
                            delta = 2*np.pi
                        else:  # G2 horaire
                            delta = -2*np.pi
                    else:
                        if G3:  # anti-horaire
                            delta = (angle_arr - angle_dep) % (2*np.pi)
                        else:  # sens == "G2" → horaire
                            delta = -((angle_dep - angle_arr) % (2*np.pi))

                    # Nombre de segments
                    nb_seg = max(2, int(abs(rayon * delta) / lg_seg))

                    # Liste des angles
                    L_angles = np.linspace(angle_dep, angle_dep + delta, nb_seg+1)
                    
                    C1 = np.round(np.cos(L_angles)*rayon+I_abs,3)
                    C2 = np.round(np.sin(L_angles)*rayon+J_abs,3)

                    first_line = True
                        
                    for i,j in zip(C1,C2) :
                        if G19 :
                            axe_1 = "Y"
                            axe_2 = "Z"
                        elif G18 :
                            axe_1 = "X"
                            axe_2 = "Z"
                        else :
                            axe_1 = "X"
                            axe_2 = "Y"

                        #Première ligne
                        if first_line :
                            first_line = False
                            new_ligne = "G1"+axe_1+str(i)+axe_2+str(j)
                            if F_ligne != None:
                                new_ligne += " F"+str(F_ligne)
                            if S_ligne != None :
                                new_ligne += " S"+str(S_ligne)
                            new_ligne += "\n"

                        else :                            
                            new_ligne = "G1"+axe_1+str(i)+axe_2+str(j)+"\n"
                        fichier_output.write(new_ligne)
                else :
                    fichier_output.write(ligne)

            elif G1 :
                precise_G1 = ""
                if "G1" in ligne :
                    precise_G1 = "G1"
                #Divise le segment en plusieurs sous-segments
                if X_ligne is not None and Y_ligne is not None :
                    x_rel = X_ligne - X_ligne_old
                    y_rel = Y_ligne - Y_ligne_old
                    lg_seg_occurs = np.sqrt(x_rel**2+y_rel**2)
                    nb_seg = max(2, int(lg_seg_occurs / lg_seg))
                    X_new = np.round(np.linspace(X_ligne_old,X_ligne,nb_seg),3)
                    Y_new = np.round(np.linspace(Y_ligne_old,Y_ligne,nb_seg),3)
                    new_ligne = f"{precise_G1}X{str(X_new[1])} Y{str(Y_new[1])}"
                    if F_ligne != None :
                        new_ligne += " F"+str(F_ligne)
                    if S_ligne != None :
                        new_ligne += " S"+str(S_ligne)
                    new_ligne += "\n"
                    fichier_output.write(new_ligne)
                    for i,j in zip(X_new[2:],Y_new[2:]) :
                        new_ligne = f"X{str(i)} Y{str(j)}\n"
                        fichier_output.write(new_ligne)

                elif X_ligne is not None :
                    x_rel = X_ligne - X_ligne_old
                    lg_seg_occurs = np.sqrt(x_rel**2)
                    nb_seg = max(2, int(lg_seg_occurs / lg_seg))
                    X_new = np.round(np.linspace(X_ligne_old,X_ligne,nb_seg),3)
                    new_ligne = f"{precise_G1}X{str(X_new[1])}"
                    if F_ligne != None :
                        new_ligne += " F"+str(F_ligne)
                    if S_ligne != None :
                        new_ligne += " S"+str(S_ligne)
                    new_ligne += "\n"
                    fichier_output.write(new_ligne)
                    for i in X_new[2:] :
                        new_ligne = f"X{str(i)}\n"
                        fichier_output.write(new_ligne)

                elif Y_ligne is not None :
                    y_rel = Y_ligne - Y_ligne_old
                    lg_seg_occurs = np.sqrt(y_rel**2)
                    nb_seg = max(2, int(lg_seg_occurs / lg_seg))
                    Y_new = np.round(np.linspace(Y_ligne_old,Y_ligne,nb_seg),3)
                    new_ligne = f"{precise_G1}Y{str(Y_new[1])}"
                    if F_ligne != None :
                        new_ligne += " F"+str(F_ligne)
                    if S_ligne != None :
                        new_ligne += " S"+str(S_ligne)
                    new_ligne += "\n"
                    fichier_output.write(new_ligne)
                    for i in Y_new[2:] :
                        new_ligne = f"Y{str(i)}\n"
                        fichier_output.write(new_ligne)

                else :
                    fichier_output.write(ligne)
                
            else :
                fichier_output.write(ligne)

def coordonnees_ligne(ligne):
    # Cherche les valeurs de X, Y et Z dans la ligne
    coord_x = re.search(r'X(-?\d+(\.\d+)?)', ligne)
    coord_y = re.search(r'Y(-?\d+(\.\d+)?)', ligne)
    coord_z = re.search(r'Z(-?\d+(\.\d+)?)', ligne)
    coord_i = re.search(r'I(-?\d+(\.\d+)?)', ligne)
    coord_j = re.search(r'J(-?\d+(\.\d+)?)', ligne)
    coord_f = re.search(r'F(-?\d+(\.\d+)?)', ligne)
    coord_s = re.search(r'S(-?\d+(\.\d+)?)', ligne)
    
    # Crée le dictionnaire avec les valeurs trouvées
    coordonnees = {}
    if coord_x:
        coordonnees['X'] = float(coord_x.group(1))
    if coord_y:
        coordonnees['Y'] = float(coord_y.group(1))
    if coord_z:
        coordonnees['Z'] = float(coord_z.group(1))
    if coord_i:
        coordonnees['I'] = float(coord_i.group(1))
    if coord_j:
        coordonnees['J'] = float(coord_j.group(1))
    if coord_f:
        coordonnees['F'] = int(coord_f.group(1))
    if coord_s:
        coordonnees['S'] = int(coord_s.group(1))
    
    return coordonnees



def interface():
    resultat = {"valeur": None}  # dictionnaire pour stocker la valeur saisie

    def valider():
        resultat["valeur"] = float(entree_var.get())
        fenetre.destroy()  # ferme la fenêtre après validation

    def verifier_saisie(*args):
        valeur = entree_var.get()
        try:
            nombre = float(valeur)
            if nombre > 0:
                bouton.config(state="normal")  # Activer le bouton
            else:
                bouton.config(state="disabled")
        except ValueError:
            bouton.config(state="disabled")

    # Création de la fenêtre principale
    fenetre = tk.Tk()
    fenetre.title("Exemple Tkinter")

    # Texte explicatif en haut
    text = "Longueur de segment en mm (ex : 0.2)"
    label_info = tk.Label(fenetre, text=text, font=("Arial", 14))
    label_info.grid(row=0, column=0, columnspan=2, pady=10)

    # Texte "longueur souhaitée" aligné avec champ
    label_longueur = tk.Label(fenetre, text="longueur souhaitée :", font=("Arial", 12))
    label_longueur.grid(row=1, column=0, padx=5, sticky="e")


    # Champ de saisie avec valeur par défaut 0.2
    dictio_param = param_standart()
    lg_seg = dictio_param['lg_seg']
    entree_var = tk.StringVar(value=str(lg_seg))
    entree_var.trace_add("write", verifier_saisie)

    entree = tk.Entry(fenetre, textvariable=entree_var, font=("Arial", 12))
    entree.grid(row=1, column=1, padx=5, pady=5)

    # Bouton valider (désactivé au départ)
    bouton = tk.Button(fenetre, text="Valider", command=valider, font=("Arial", 12))
    bouton.grid(row=2, column=0, columnspan=2, pady=10)

    # Ajustement des colonnes
    fenetre.grid_columnconfigure(0, weight=1)
    fenetre.grid_columnconfigure(1, weight=1)

    fenetre.mainloop()

    return resultat["valeur"]



def selection_gcode():
    def browse_file():
        filepath = filedialog.askopenfilename(
            title="Sélectionnez un fichier G-CODE",
            filetypes=[("G-CODE files", "*.gcode *.nc *.txt"), ("Tous les fichiers", "*.*")]
        )
        if filepath:
            entry_var.set(filepath)
            validate_button.config(state=tk.NORMAL)

    def validate():
        path_select = entry_var.get()
        if path_select:
            print(f"G-CODE sélectionné : {path_select}")
            root.quit()  # stop mainloop
        else:
            messagebox.showwarning("Attention", "Veuillez sélectionner un fichier G-CODE")

    # Créer la fenêtre principale
    root = tk.Tk()
    root.title("Sélection G-CODE")

    # Dimensions de la fenêtre
    window_width = 500
    window_height = 150

    # Obtenir dimensions écran
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Position X (collé à gauche avec une petite marge)
    pos_x = 50  
    # Position Y (centré verticalement)
    pos_y = (screen_height // 2) - (window_height // 2)

    # Appliquer géométrie
    root.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")

    # Texte d’instruction
    label = tk.Label(root, text="Sélectionnez un fichier G-CODE :")
    label.pack(pady=10)

    # Champ texte + bouton parcourir
    entry_var = tk.StringVar()
    entry = tk.Entry(root, textvariable=entry_var, width=60)
    entry.pack(padx=10, pady=5)

    browse_button = tk.Button(root, text="Parcourir", command=browse_file)
    browse_button.pack(pady=5)

    # Bouton Valider (désactivé par défaut)
    validate_button = tk.Button(root, text="Valider", state=tk.DISABLED, command=validate)
    validate_button.pack(pady=10)

    root.mainloop()

    selected_path = entry_var.get()
    root.destroy()
    return selected_path

def modify_filename(path, suffix="", new_ext=None):
    """
    Modifie le nom du fichier (avant extension) en ajoutant un suffixe
    et éventuellement change l'extension.

    Arguments :
        path (str)     : chemin complet du fichier
        suffix (str)   : texte à ajouter avant l'extension (ex: "_mod")
        new_ext (str)  : nouvelle extension (ex: ".txt" ou "txt").
                         Si None, garde l'extension existante.

    Retourne :
        str : nouveau chemin du fichier
    """
    directory, filename = os.path.split(path)
    name, ext = os.path.splitext(filename)

    # Normaliser l’extension (ajouter le "." si absent)
    if new_ext is not None:
        if not new_ext.startswith("."):
            new_ext = "." + new_ext
    else:
        new_ext = ext

    new_filename = f"{name}{suffix}{new_ext}"
    return os.path.join(directory, new_filename)


if __name__ == "__main__" :
    main(False)
