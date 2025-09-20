
import Link from 'next/link';

const Sidebar = () => {
  const menuItems = [
    { name: 'Dashboard', path: '/' },
    { name: 'CRM', path: '/crm' },
    { name: 'ERP', path: '/erp' },
    { name: 'CMS', path: '/cms' },
  ];

  return (
    <aside className="w-64 h-screen bg-brand-primary text-brand-on-primary flex flex-col">
      <div className="p-6 text-2xl font-semibold">TravelHub</div>
      <nav className="flex-1 px-4 py-4">
        <ul>
          {menuItems.map((item) => (
            <li key={item.name}>
              <Link href={item.path} className="block px-4 py-2 rounded-md hover:bg-brand-secondary">
                {item.name}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
};

export default Sidebar;
