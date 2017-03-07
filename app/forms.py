from wtforms import Form, StringField, validators

class SignUpForm(Form):
    email = StringField('email', [validators.Length(min=6, max=255), validators.Email(message=None)])