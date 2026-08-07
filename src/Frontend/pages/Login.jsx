import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Lock, LogIn, Mail, Sparkles } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import '../styles/pages/Login.css'

function Login() {
  const { login } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  function handleSubmit(event) {
    event.preventDefault()

    if (email) {
      login(email)
      navigate('/')
    }
  }

  return (
    <main className="login-page">
      <section className="login-page__card">
        <Link className="login-page__back" to="/">
          <ArrowLeft className="login-page__back-icon" />
          <span>{t.backToHome}</span>
        </Link>

        <div className="login-page__heading">
          <div className="login-page__mark">
            <Sparkles className="login-page__mark-icon" />
          </div>
          <h1>{t.loginTitle}</h1>
          <p>{t.loginSubtitle}</p>
        </div>

        <form className="login-page__form" onSubmit={handleSubmit}>
          <div className="login-page__field">
            <label className="login-page__label" htmlFor="login-email">
              <Mail className="login-page__label-icon" />
              <span>{t.emailAddress}</span>
            </label>
            <input
              className="login-page__input"
              id="login-email"
              type="email"
              required
              placeholder="victoria@vintravel.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="login-page__field">
            <label className="login-page__label" htmlFor="login-password">
              <Lock className="login-page__label-icon" />
              <span>{t.password}</span>
            </label>
            <input
              className="login-page__input"
              id="login-password"
              type="password"
              required
              placeholder="••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          <button className="login-page__submit" type="submit">
            <LogIn className="login-page__submit-icon" />
            <span>{t.signIn}</span>
          </button>
        </form>

        <p className="login-page__register">
          {t.noAccount}{' '}
          <Link to="/register">{t.registerHere}</Link>
        </p>
      </section>
    </main>
  )
}

export default Login
