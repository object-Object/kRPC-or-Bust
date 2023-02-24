# these types ONLY exist as stubs so this error isn't helpful
# pyright: reportMissingModuleSource = false

from typing import TYPE_CHECKING

from ._Stub import Stub

if TYPE_CHECKING:
    from krpc.ui import UI
else:
    UI = Stub()

# Built-in types

RectTransform = UI.RectTransform

Canvas = UI.Canvas
Panel = UI.Panel
Text = UI.Text
Button = UI.Button
InputField = UI.InputField

# Additional helper types

UIElement = Canvas | Panel | Text | Button | InputField
