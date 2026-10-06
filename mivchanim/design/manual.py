"""Hand-built blocks for the few pages whose layout is too irregular for the generic parser."""


def R(t, f=''):
    return [[t, f]]


def Q(text, subs, lines_labels, kicker='שאלה'):
    return dict(t='q', label=None, kicker=kicker, runs=R(text), more=[], subs=[dict(label=l, runs=R(x)) for l, x in subs], n=None, sublines=lines_labels)


BLOCKS = {
    'u26': [
        dict(t='h3', runs=R('להזהר מצואה בשעת קריאת שמע')),
        Q('האם שרי לקרות כנגד צואה', [('א', 'בעששית בתוך ד"א ממקום שכלה הריח.'), ('ב', 'בגומה ומכסה ברגלו או בסנדלו.'), ('ג', 'המונח בתוף עביט מלא מים.')], ['א', 'ב', 'ג']),
        Q('האם שרי לקרוא ק"ש', [('א', 'בצואה בגומא ומכסנה ברגלו.'), ('ב', 'כנ"ל ומכסנה בסנדלו שעל רגלו.'), ('ג', 'כנ"ל ומכסנה בסנדלו שאינו לבוש בה.'), ('ד', 'בצואה דבוקה ברגלו ומכסנה ע"י לבישת סנדלו.')], ['א', 'ב', 'ג', 'ד']),
        dict(t='closenote', runs=R('גמר חתימה טובה')),
    ],
}
