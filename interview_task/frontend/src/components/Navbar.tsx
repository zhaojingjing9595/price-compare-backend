import { NavLink } from 'react-router-dom'

function Navbar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `text-sm font-medium ${isActive ? 'text-black' : 'text-gray-500 hover:text-gray-800'}`

  return (
    <nav className="flex items-center justify-between px-8 py-4 border-b border-gray-200">
      <span className="font-bold text-lg">Price Compare</span>
      <ul className="flex gap-6 list-none m-0 p-0">
        <li>
          <NavLink to="/" end className={linkClass}>
            Home
          </NavLink>
        </li>
        <li>
          <NavLink to="/products" className={linkClass}>
            Products
          </NavLink>
        </li>
        <li>
          <NavLink to="/stores" className={linkClass}>
            Stores
          </NavLink>
        </li>
      </ul>
    </nav>
  )
}

export default Navbar