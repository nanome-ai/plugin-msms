import os

import nanome
from nanome import ui
from nanome.util import async_callback, enums, Color

from .MSMSInstance import COLOR_BY_OPTIONS, COLOR_PRESETS, MSMSInstance

BASE_DIR = os.path.join(os.path.dirname(__file__))
MENU_PATH = os.path.join(BASE_DIR, 'assets/menu.json')
SURFACE_ITEM_PATH = os.path.join(BASE_DIR, 'assets/surface_item.json')
DELETE_ICON = os.path.join(BASE_DIR, 'assets/delete.png')
VISIBLE_ICON = os.path.join(BASE_DIR, 'assets/visible.png')
INVISIBLE_ICON = os.path.join(BASE_DIR, 'assets/invisible.png')

NO_CALLBACK = lambda *_: None

class MSMS(nanome.AsyncPluginInstance):
    def start(self):
        self.set_plugin_list_button(self.PluginListButtonType.run, 'Open')

        self.selected_complex: nanome.structure.Complex = None
        self.selected_chains: set[str] = set()
        self.selection_only = False

        self.selected_surface_btn: ui.Button = None
        self.selected_surface: MSMSInstance = None
        self.surfaces: list[MSMSInstance] = []

        self.create_menu()
        self.on_run()

    @async_callback
    async def on_run(self):
        self.menu.enabled = True
        self.update_menu(self.menu)

    def on_complex_list_changed(self):
        self.update_entry_list()

    def create_menu(self):
        self.menu = ui.Menu.io.from_json(MENU_PATH)
        root: ui.LayoutNode = self.menu.root

        self.pfb_surface: ui.LayoutNode = ui.LayoutNode.io.from_json(SURFACE_ITEM_PATH)
        self.pfb_surface.find_node('Button Delete').get_content().icon.value.set_all(DELETE_ICON)

        self.btn_tab1: ui.Button = root.find_node('Tab Generate').get_content()
        self.btn_tab2: ui.Button = root.find_node('Tab View').get_content()
        self.btn_tab1.register_pressed_callback(self.change_tab)
        self.btn_tab2.register_pressed_callback(self.change_tab)

        self.ln_tab1: ui.LayoutNode = root.find_node('Tab 1')
        self.ln_tab2: ui.LayoutNode = root.find_node('Tab 2')

        # tab 1
        self.ln_chains: ui.LayoutNode = root.find_node('Chains')
        self.ln_no_entry: ui.LayoutNode = root.find_node('No Entry')
        self.dd_entries: ui.Dropdown = root.find_node('Dropdown Entry').get_content()
        self.dd_entries.register_item_clicked_callback(self.select_entry)
        self.lst_chains: ui.UIList = root.find_node('List Chains').get_content()

        self.btn_all_chains: ui.Button = root.find_node('Button All Chains').get_content()
        self.btn_all_chains.register_pressed_callback(self.toggle_all_chains)
        self.btn_all_chains.toggle_on_press = True

        self.lbl_selection: ui.Label = root.find_node('Label Selection').get_content()
        ln_selection_only: ui.LayoutNode = root.find_node('Button Selection Only')
        self.btn_selection_only: ui.Button = ln_selection_only.add_new_toggle_switch('Selection Only')
        self.btn_selection_only.register_pressed_callback(self.toggle_selection_only)

        self.btn_generate: ui.Button = root.find_node('Button Generate').get_content()
        self.btn_generate.register_pressed_callback(self.generate_msms)
        self.btn_generate.disable_on_press = True

        # tab 2
        self.lst_surfaces: ui.UIList = root.find_node('List Surfaces').get_content()
        self.btn_toggle_all: ui.Button = root.find_node('Button Toggle All').get_content()
        self.btn_delete_all: ui.Button = root.find_node('Button Delete All').get_content()
        self.btn_toggle_all.register_pressed_callback(self.toggle_all_surfaces)
        self.btn_delete_all.register_pressed_callback(self.delete_all_surfaces)

        self.ln_color_options: ui.LayoutNode = root.find_node('Color Options')
        self.ln_no_surface: ui.LayoutNode = root.find_node('No Surface')

        self.dd_color_by: ui.Dropdown = root.find_node('Dropdown Color By').get_content()
        self.dd_preset: ui.Dropdown = root.find_node('Dropdown Preset').get_content()
        self.dd_color_by.register_item_clicked_callback(self.select_color_by)
        self.dd_preset.register_item_clicked_callback(self.select_preset)

        self.sld_red: ui.Slider = root.find_node('Slider Red').get_content()
        self.sld_green: ui.Slider = root.find_node('Slider Green').get_content()
        self.sld_blue: ui.Slider = root.find_node('Slider Blue').get_content()
        self.sld_alpha: ui.Slider = root.find_node('Slider Alpha').get_content()
        self.sld_red.register_released_callback(self.update_color)
        self.sld_green.register_released_callback(self.update_color)
        self.sld_blue.register_released_callback(self.update_color)
        self.sld_alpha.register_released_callback(self.update_color)

        self.inp_red: ui.TextInput = root.find_node('Input Red').get_content()
        self.inp_green: ui.TextInput = root.find_node('Input Green').get_content()
        self.inp_blue: ui.TextInput = root.find_node('Input Blue').get_content()
        self.inp_alpha: ui.TextInput = root.find_node('Input Alpha').get_content()
        self.inp_red.register_submitted_callback(self.update_color)
        self.inp_green.register_submitted_callback(self.update_color)
        self.inp_blue.register_submitted_callback(self.update_color)
        self.inp_alpha.register_submitted_callback(self.update_color)

        self.init_color_dropdowns()
        self.update_entry_list()
        self.update_selection_text()
        self.update_surface_list()

    def init_color_dropdowns(self):
        self.dd_color_by.items.clear()
        for name, value in COLOR_BY_OPTIONS:
            ddi = ui.DropdownItem(name)
            ddi.value = value
            self.dd_color_by.items.append(ddi)
        self.dd_color_by.items[0].selected = True

        self.dd_preset.items.clear()
        for name, color in COLOR_PRESETS:
            color_name = f'<size=120%><color={color}>■</color></size> {name}'
            ddi = ui.DropdownItem(color_name)
            ddi.value = color
            self.dd_preset.items.append(ddi)
        self.dd_preset.items[0].selected = True

        self.update_content(self.dd_color_by, self.dd_preset)

    def change_tab(self, btn: ui.Button):
        is_tab1 = btn == self.btn_tab1
        self.btn_tab1.selected = is_tab1
        self.btn_tab2.selected = not is_tab1
        self.ln_tab1.enabled = is_tab1
        self.ln_tab2.enabled = not is_tab1
        self.update_menu(self.menu)

    @async_callback
    async def update_entry_list(self):
        complexes = await self.request_complex_list()
        self.dd_entries.items.clear()
        for complex in complexes:
            ddi = ui.DropdownItem(complex.full_name)
            ddi.index = complex.index
            self.dd_entries.items.append(ddi)
        self.update_content(self.dd_entries)

        indices = [complex.index for complex in complexes]
        update_surface_list = False
        for surface in self.surfaces:
            if surface.index in indices:
                update_surface_list = True
                surface.destroy()
        if update_surface_list:
            self.update_surface_list()

    @async_callback
    async def select_entry(self, dd: ui.Dropdown, ddi: ui.DropdownItem):
        self.lst_chains.items.clear()
        ln = ui.LayoutNode()
        lbl = ln.add_new_label('loading chains...')
        lbl.text_auto_size = False
        lbl.text_size = 0.3
        lbl.text_horizontal_align = enums.HorizAlignOptions.Middle
        lbl.text_vertical_align = enums.VertAlignOptions.Bottom
        self.lst_chains.items.append(ln)

        self.ln_no_entry.enabled = False
        self.ln_chains.enabled = True
        self.update_node(self.ln_no_entry, self.ln_chains)

        if self.selected_complex:
            self.selected_complex.register_complex_updated_callback(NO_CALLBACK)
            self.selected_complex.register_selection_changed_callback(NO_CALLBACK)

        def update_complex(complex):
            self.selected_complex = complex
            self.update_selection_text()

        complexes = await self.request_complexes([ddi.index])
        self.selected_complex: nanome.structure.Complex = complexes[0]
        self.selected_complex.register_complex_updated_callback(update_complex)
        self.selected_complex.register_selection_changed_callback(update_complex)
        self.selected_chains = set()
        self.btn_all_chains.selected = False

        self.lst_chains.items.clear()
        for chain in self.selected_complex.chains:
            ln = ui.LayoutNode()
            btn = ln.add_new_button(chain.name)
            btn.chain = chain.name
            btn.toggle_on_press = True
            btn.register_pressed_callback(self.select_chain)
            self.lst_chains.items.append(ln)
        self.update_content(self.lst_chains, self.btn_all_chains)
        self.update_selection_text()

    def select_chain(self, btn: ui.Button):
        if btn.selected:
            self.selected_chains.add(btn.chain)
        else:
            self.selected_chains.remove(btn.chain)

        all_selected = len(self.selected_chains) == len(list(self.selected_complex.chains))
        self.btn_all_chains.selected = all_selected
        self.update_content(self.btn_all_chains)
        self.update_selection_text()

    def toggle_all_chains(self, btn: ui.Button):
        if btn.selected:
            self.selected_chains = set(chain.name for chain in self.selected_complex.chains)
        else:
            self.selected_chains.clear()

        for ln in self.lst_chains.items:
            ln.get_content().selected = btn.selected

        self.update_content(self.lst_chains)
        self.update_selection_text()

    def toggle_selection_only(self, btn: ui.Button):
        self.selection_only = btn.selected
        self.update_selection_text()

    def update_selection_text(self):
        num_atoms = 0
        if not self.selected_complex:
            self.lbl_selection.text_value = 'No entry selected'
        elif not self.selected_chains:
            self.lbl_selection.text_value = 'No chains selected'
        else:
            num_chains = len(self.selected_chains)
            for chain in self.selected_complex.chains:
                if chain.name not in self.selected_chains:
                    continue
                for atom in chain.atoms:
                    if self.selection_only and not atom.selected:
                        continue
                    num_atoms += 1

            chains_text = f'{num_chains} chain{"s" if num_chains != 1 else ""} selected'
            atoms_text = f'{num_atoms} atom{"s" if num_atoms != 1 else ""} selected'
            self.lbl_selection.text_value = f'{chains_text}\n{atoms_text}'

        self.btn_generate.unusable = num_atoms == 0
        self.update_content(self.lbl_selection, self.btn_generate)

    @async_callback
    async def generate_msms(self, btn: ui.Button):
        chain_names = ', '.join(sorted(self.selected_chains))
        name = f'{self.selected_complex.full_name} <size=50%>{chain_names}</size>'
        index = self.selected_complex.index
        atoms = []

        for chain in self.selected_complex.chains:
            if chain.name not in self.selected_chains:
                continue
            for atom in chain.atoms:
                if self.selection_only and not atom.selected:
                    continue
                atoms.append(atom)

        btn.text.value.set_all('Generating...')
        btn.unusable = True
        self.update_content(self.btn_generate)

        try:
            surface = MSMSInstance(name, index, atoms)
            await surface.generate()
            self.surfaces.append(surface)

            self.selected_surface = surface
            self.update_surface_list()
            self.change_tab(self.btn_tab2)
            self.select_surface(self.selected_surface_btn)
        except Exception as e:
            nanome.util.Logs.error(e)
            self.send_notification(enums.NotificationTypes.error, 'Error generating surface')

        btn.text.value.set_all('Generate')
        btn.unusable = False
        self.update_content(self.btn_generate)

    def update_surface_list(self):
        self.lst_surfaces.items.clear()
        for surface in self.surfaces:
            ln: ui.LayoutNode = self.pfb_surface.clone()
            lbl: ui.Label = ln.find_node('Label').get_content()
            lbl.text_value = surface.name

            btn: ui.Button = ln.get_content()
            btn.surface = surface
            if self.selected_surface == surface:
                btn.selected = True
                self.selected_surface_btn = btn
            btn.register_pressed_callback(self.select_surface)

            btn_toggle: ui.Button = ln.find_node('Button Toggle').get_content()
            btn_toggle.register_pressed_callback(self.toggle_surface)
            btn_toggle.icon.value.set_all(VISIBLE_ICON if surface.visible else INVISIBLE_ICON)
            btn_toggle.surface = surface

            btn_delete: ui.Button = ln.find_node('Button Delete').get_content()
            btn_delete.register_pressed_callback(self.delete_surface)
            btn_delete.surface = surface

            self.lst_surfaces.items.append(ln)

        if not self.surfaces:
            ln = ui.LayoutNode()
            lbl = ln.add_new_label('no surfaces')
            lbl.text_auto_size = False
            lbl.text_size = 0.3
            lbl.text_horizontal_align = enums.HorizAlignOptions.Middle
            lbl.text_vertical_align = enums.VertAlignOptions.Bottom
            self.lst_surfaces.items.append(ln)

        any_visible = any(surface.visible for surface in self.surfaces)
        self.btn_toggle_all.text.value.set_all('Hide All' if any_visible else 'Show All')
        self.btn_toggle_all.unusable = not self.surfaces
        self.btn_delete_all.unusable = not self.surfaces
        self.update_content(self.lst_surfaces, self.btn_toggle_all, self.btn_delete_all)

        if not self.surfaces:
            self.ln_color_options.enabled = False
            self.ln_no_surface.enabled = True
            self.update_node(self.ln_color_options, self.ln_no_surface)

    def select_surface(self, btn: ui.Button):
        if self.selected_surface_btn:
            self.selected_surface_btn.selected = False
            self.update_content(self.selected_surface_btn)

        surface: MSMSInstance = btn.surface
        self.selected_surface_btn = btn
        self.selected_surface = surface
        btn.selected = True

        self.ln_color_options.enabled = True
        self.ln_no_surface.enabled = False

        self.update_color_dropdowns()
        self.update_color_inputs()
        self.update_content(btn)
        self.update_node(self.ln_color_options, self.ln_no_surface)

    def toggle_surface(self, btn: ui.Button):
        btn.surface.toggle_visible()
        self.update_surface_list()

    def delete_surface(self, btn: ui.Button):
        btn.surface.destroy()
        self.surfaces.remove(btn.surface)
        self.update_surface_list()

    def toggle_all_surfaces(self, btn: ui.Button):
        show = btn.text.value.idle == 'Show All'
        for surface in self.surfaces:
            surface.toggle_visible(show)
        self.update_surface_list()

    def delete_all_surfaces(self, btn: ui.Button):
        for surface in self.surfaces:
            surface.destroy()
        del self.surfaces[:]
        self.update_surface_list()

    def select_color_by(self, dd: ui.Dropdown, ddi: ui.DropdownItem):
        self.selected_surface.color_by = ddi.value
        self.selected_surface.apply_color()

    def select_preset(self, dd: ui.Dropdown, ddi: ui.DropdownItem):
        surface = self.selected_surface
        surface.hex_color = ddi.value
        self.update_color_inputs()
        surface.apply_color()

    def update_color(self, ui):
        to_update = [self.dd_preset]
        pairs = [
            (self.sld_red, self.inp_red),
            (self.sld_green, self.inp_green),
            (self.sld_blue, self.inp_blue),
            (self.sld_alpha, self.inp_alpha),
        ]
        for sld, inp in pairs:
            if ui == sld:
                inp.input_text = int(sld.current_value)
                to_update.append(inp)
            elif ui == inp:
                sld.current_value = float(inp.input_text)
                to_update.append(sld)

        r = int(self.sld_red.current_value)
        g = int(self.sld_green.current_value)
        b = int(self.sld_blue.current_value)
        a = int(255 * self.sld_alpha.current_value / 100)

        self.selected_surface.color = Color(r, g, b, a)
        self.update_color_dropdowns()
        self.update_content(to_update)
        self.selected_surface.apply_color()

    def update_color_dropdowns(self):
        for ddi in self.dd_color_by.items:
            ddi.selected = False
            if ddi.value == self.selected_surface.color_by:
                ddi.selected = True

        is_custom = True
        for ddi in self.dd_preset.items:
            ddi.selected = False
            if ddi.value == self.selected_surface.hex_color:
                is_custom = False
                ddi.selected = True

        if is_custom:
            ddi = self.dd_preset.items[0]
            ddi.selected = True
            color = self.selected_surface.hex_color
            ddi.name = f'<size=120%><color={color}>■</color></size> Custom'
            ddi.value = color

    def update_color_inputs(self):
        surface = self.selected_surface

        self.inp_red.input_text = self.sld_red.current_value = surface.color.r
        self.inp_green.input_text = self.sld_green.current_value = surface.color.g
        self.inp_blue.input_text = self.sld_blue.current_value = surface.color.b
        self.inp_alpha.input_text = self.sld_alpha.current_value = int(100 * surface.color.a / 255)

        self.update_content(
            self.sld_red, self.sld_green, self.sld_blue, self.sld_alpha,
            self.inp_red, self.inp_green, self.inp_blue, self.inp_alpha)


def main():
    plugin = nanome.Plugin("MSMS", "Run MSMS and load the molecular surface in Nanome.", "Computation", False)
    plugin.set_plugin_class(MSMS)
    plugin.run()

if __name__ == "__main__":
    main()