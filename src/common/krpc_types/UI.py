# these types ONLY exist as stubs until runtime so this error isn't helpful
# pyright: reportMissingModuleSource = false

from krpc.ui import UI

# Built-in types

RectTransform = UI.RectTransform

Canvas = UI.Canvas
Panel = UI.Panel
Text = UI.Text
Button = UI.Button
InputField = UI.InputField

# Additional helper types

UIElement = Canvas | Panel | Text | Button | InputField
