import tkinter as tk
from tkinter import ttk, messagebox

# --- CONFIGURACIÓN DE VALORES COMERCIALES ---
# E12 para 10% de tolerancia, E24 para 1% de tolerancia
E12_MULTIPLIERS = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
E24_MULTIPLIERS = [
    1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 
    2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 
    6.8, 7.5, 8.2, 9.1
]

def get_commercial_values(tolerance):
    multipliers = E12_MULTIPLIERS if tolerance == "10%" else E24_MULTIPLIERS
    values = []
    # Generar décadas desde 1 Ohm hasta 10 Megaohms
    for decade in range(0, 7):
        factor = 10 ** decade
        for m in multipliers:
            val = m * factor
            if val <= 10_000_000: # Límite superior razonable de 10M
                values.append(val)
    return sorted(list(set(values)))

def format_resistance(val):
    if val >= 1_000_000:
        return f"{val/1_000_000:.2f} MΩ"
    elif val >= 1_000:
        return f"{val/1_000:.2f} kΩ"
    else:
        return f"{val:.2f} Ω"

# --- MOTOR DE CÁLCULO DE COMBINACIONES ---
def find_best_combinations(target, tolerance, max_resistors=3, limit=15):
    all_resistors = get_commercial_values(tolerance)
    
    # Filtrar valores en un rango razonable (0.1x a 10x del objetivo) para eficiencia
    filtered_resistors = [r for r in all_resistors if 0.1 * target <= r <= 10 * target]
    if not filtered_resistors:
        filtered_resistors = all_resistors # Fallback si el target es muy extremo

    results = []

    def add_result(eq_val, desc, comp_list):
        error = abs(eq_val - target)
        error_pct = (error / target) * 100
        results.append({
            'eq': eq_val,
            'desc': desc,
            'comps': comp_list,
            'error': error_pct
        })

    # 1. Una sola resistencia
    if max_resistors >= 1:
        for r1 in filtered_resistors:
            add_result(r1, f"{format_resistance(r1)} (1 Resistencia)", [r1])

    # 2. Dos resistencias
    if max_resistors >= 2:
        for i, r1 in enumerate(filtered_resistors):
            for r2 in filtered_resistors[i:]:
                # Serie: R1 + R2
                s_val = r1 + r2
                add_result(s_val, f"{format_resistance(r1)} + {format_resistance(r2)} [Serie]", [r1, r2])
                
                # Paralelo: (R1 * R2) / (R1 + R2)
                p_val = (r1 * r2) / (r1 + r2)
                add_result(p_val, f"{format_resistance(r1)} || {format_resistance(r2)} [Paralelo]", [r1, r2])

    # 3. Tres resistencias
    if max_resistors >= 3:
        # Para evitar bucles excesivamente lentos, tomamos una muestra representativa o el conjunto filtrado
        subset = filtered_resistors[::2] if len(filtered_resistors) > 50 else filtered_resistors
        for i, r1 in enumerate(subset):
            for j, r2 in enumerate(subset[i:], i):
                for r3 in subset[j:]:
                    # Serie pura: R1 + R2 + R3
                    s_val = r1 + r2 + r3
                    add_result(s_val, f"({format_resistance(r1)} + {format_resistance(r2)} + {format_resistance(r3)}) [Serie]", [r1, r2, r3])
                    
                    # Paralelo puro: 1 / (1/R1 + 1/R2 + 1/R3)
                    p_val = 1.0 / ((1.0/r1) + (1.0/r2) + (1.0/r3))
                    add_result(p_val, f"({format_resistance(r1)} || {format_resistance(r2)} || {format_resistance(r3)}) [Paralelo]", [r1, r2, r3])
                    
                    # Mixtas comunes: (R1 || R2) + R3
                    m1 = (r1 * r2) / (r1 + r2) + r3
                    add_result(m1, f"({format_resistance(r1)} || {format_resistance(r2)}) + {format_resistance(r3)} [Mixta]", [r1, r2, r3])
                    
                    # Mixtas comunes: (R1 + R2) || R3
                    if (r1 + r2) > 0:
                        m2 = ((r1 + r2) * r3) / ((r1 + r2) + r3)
                        add_result(m2, f"({format_resistance(r1)} + {format_resistance(r2)}) || {format_resistance(r3)} [Mixta]", [r1, r2, r3])

    # Ordenar por menor porcentaje de error
    results = sorted(results, key=lambda x: x['error'])
    
    # Filtrar duplicados aproximados de valor equivalente
    unique_results = []
    seen = set()
    for res in results:
        key = round(res['eq'], 4)
        if key not in seen:
            seen.add(key)
            unique_results.append(res)
        if len(unique_results) >= limit:
            break
            
    return unique_results

# --- INTERFAZ GRÁFICA (DARK MODE MATTE) ---
class ResistorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Calculadora de Redes de Resistencias Comerciales")
        self.root.geometry("850x650")
        self.root.configure(bg="#121212")
        
        # Estilos personalizados
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Configuración de colores oscuros para la tabla y widgets
        self.style.configure(".", background="#1e1e1e", foreground="#ffffff", fieldbackground="#2d2d2d")
        self.style.configure("Treeview", background="#1e1e1e", foreground="#ffffff", fieldbackground="#1e1e1e", rowheight=28, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", background="#2d2d2d", foreground="#00adb5", font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[('selected', '#00adb5')], foreground=[('selected', '#ffffff')])

        self.create_widgets()

    def create_widgets(self):
        # Header / Título
        header_frame = tk.Frame(self.root, bg="#1e1e1e", padx=20, pady=15)
        header_frame.pack(fill="x", padx=15, pady=15)
        
        title_label = tk.Label(header_frame, text="Calculadora de Combinaciones de Resistencias", font=("Segoe UI", 16, "bold"), fg="#00adb5", bg="#1e1e1e")
        title_label.pack(anchor="w")
        subtitle_label = tk.Label(header_frame, text="Encuentra arreglos óptimos (1, 2 o 3 resistencias en serie/paralelo/mixto)", font=("Segoe UI", 9), fg="#aaaaaa", bg="#1e1e1e")
        subtitle_label.pack(anchor="w", pady=(2, 0))

        # Panel de Controles (Inputs)
        control_frame = tk.Frame(self.root, bg="#1e1e1e", padx=20, pady=15)
        control_frame.pack(fill="x", padx=15)

        # Target Resistance
        lbl_target = tk.Label(control_frame, text="Resistencia Objetivo (Ω):", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#1e1e1e")
        lbl_target.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.entry_target = tk.Entry(control_frame, font=("Segoe UI", 11), bg="#2d2d2d", fg="#ffffff", insertbackground="white", relief="flat", width=15)
        self.entry_target.grid(row=0, column=1, padx=5, pady=5, ipady=4)
        self.entry_target.insert(0, "330")

        # Tolerancia
        lbl_tol = tk.Label(control_frame, text="Tolerancia Serie:", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#1e1e1e")
        lbl_tol.grid(row=0, column=2, sticky="w", padx=15, pady=5)
        
        self.combo_tol = ttk.Combobox(control_frame, values=["10%", "1%"], state="readonly", width=8, font=("Segoe UI", 10))
        self.combo_tol.grid(row=0, column=3, padx=5, pady=5)
        self.combo_tol.set("10%")

        # Botón Calcular
        btn_calc = tk.Button(control_frame, text="Calcular Mejores", font=("Segoe UI", 10, "bold"), bg="#00adb5", fg="#ffffff", activebackground="#007f86", activeforeground="#ffffff", relief="flat", padx=15, pady=6, cursor="hand2", command=self.calculate)
        btn_calc.grid(row=0, column=4, padx=20, pady=5)

        # Panel de Resultados (Tabla)
        result_frame = tk.Frame(self.root, bg="#1e1e1e", padx=15, pady=15)
        result_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        lbl_res = tk.Label(result_frame, text="Mejores Combinaciones Comerciales Encontradas:", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#1e1e1e")
        lbl_res.pack(anchor="w", pady=(0, 10))

        # Treeview con Scrollbar
        tree_scroll = ttk.Scrollbar(result_frame)
        tree_scroll.pack(side="right", fill="y")

        self.tree = ttk.Treeview(result_frame, columns=("topologia", "valor_eq", "error"), show="headings", yscrollcommand=tree_scroll.set, height=12)
        self.tree.heading("topologia", text="Topología y Componentes")
        self.tree.heading("valor_eq", text="Valor Equivalente")
        self.tree.heading("error", text="Error (%)")
        
        self.tree.column("topologia", width=420, anchor="w")
        self.tree.column("valor_eq", width=150, anchor="center")
        self.tree.column("error", width=100, anchor="center")
        
        self.tree.pack(fill="both", expand=True)
        tree_scroll.config(command=self.tree.yview)

    def calculate(self):
        try:
            target_val = float(self.entry_target.get())
            if target_val <= 0:
                raise ValueError("El valor debe ser mayor a 0.")
        except ValueError:
            messagebox.showerror("Error de Entrada", "Por favor, introduce un valor numérico válido para la resistencia objetivo.")
            return

        tolerance = self.combo_tol.get()
        
        # Limpiar tabla anterior
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Obtener resultados
        results = find_best_combinations(target_val, tolerance, max_resistors=3, limit=12)

        if not results:
            messagebox.showinfo("Sin resultados", "No se encontraron combinaciones cercanas.")
            return

        # Insertar en la tabla
        for r in results:
            self.tree.insert("", "end", values=(
                r['desc'],
                format_resistance(r['eq']),
                f"{r['error']:.3f} %"
            ))

if __name__ == "__main__":
    root = tk.Tk()
    app = ResistorApp(root)
    root.mainloop()