import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Lock, Mail, Sparkles, User, UserPlus } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import '../styles/pages/Register.css'

function Register() {
  const { login } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  function handleSubmit(event) {
    event.preventDefault()

    if (email) {
      login(email, name)
      navigate('/')
    }
  }

  return (
    <main className="register-page">
      <section className="register-page__card">
        <Link className="register-page__back" to="/">
          <ArrowLeft className="register-page__back-icon" />
          <span>{t.backToHome}</span>
        </Link>

        <div className="register-page__heading">
          <div className="register-page__mark">
            <Sparkles className="register-page__mark-icon" />
          </div>
          <h1>{t.registerTitle}</h1>
          <p>{t.registerSubtitle}</p>
        </div>

        <form className="register-page__form" onSubmit={handleSubmit}>
          <div className="register-page__field">
            <label className="register-page__label" htmlFor="register-name">
              <User className="register-page__label-icon" />
              <span>{t.fullName}</span>
            </label>
            <input
              className="register-page__input"
              id="register-name"
              type="text"
              required
              placeholder="Victoria Tran"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>

          <div className="register-page__field">
            <label className="register-page__label" htmlFor="register-email">
              <Mail className="register-page__label-icon" />
              <span>{t.emailAddress}</span>
            </label>
            <input
              className="register-page__input"
              id="register-email"
              type="email"
              required
              placeholder="guest@vintravel.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="register-page__field">
            <label className="register-page__label" htmlFor="register-password">
              <Lock className="register-page__label-icon" />
              <span>{t.password}</span>
            </label>
            <input
              className="register-page__input"
              id="register-password"
              type="password"
              required
              placeholder="••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          <button className="register-page__submit" type="submit">
            <UserPlus className="register-page__submit-icon" />
            <span>{t.createAccount}</span>
          </button>
        </form>

        <p className="register-page__login">
          {t.alreadyHaveAccount} <Link to="/login">{t.signIn}</Link>
        </p>
      </section>
    </main>
  )
}

export default Register
