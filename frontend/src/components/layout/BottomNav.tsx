'use client';

import React, { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { BottomNavigation, BottomNavigationAction, Paper } from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import PeopleIcon from '@mui/icons-material/People';
import BusinessCenterIcon from '@mui/icons-material/BusinessCenter';
import MenuIcon from '@mui/icons-material/Menu';
import MoreMenu from './MoreMenu';

const BottomNav = () => {
  const router = useRouter();
  const pathname = usePathname();
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);

  const getActiveValue = () => {
    if (pathname.startsWith('/crm')) return '/crm';
    if (pathname.startsWith('/erp')) return '/erp';
    if (pathname === '/') return '/';
    return ''; // No active value for other paths
  };

  const [value, setValue] = useState(getActiveValue());

  const handleChange = (event: React.SyntheticEvent, newValue: string) => {
    setValue(newValue);
    if (newValue === 'more') {
      setMoreMenuOpen(true);
    } else {
      router.push(newValue);
    }
  };

  return (
    <>
      <Paper 
        sx={{ 
          position: 'fixed', 
          bottom: 0, 
          left: 0, 
          right: 0,
          display: { xs: 'block', lg: 'none' }, // Show only on mobile
          zIndex: 1100 // Ensure it's above other content
        }} 
        elevation={3}
      >
        <BottomNavigation
          showLabels
          value={value}
          onChange={handleChange}
        >
          <BottomNavigationAction label="Dashboard" value="/" icon={<DashboardIcon />} />
          <BottomNavigationAction label="CRM" value="/crm" icon={<PeopleIcon />} />
          <BottomNavigationAction label="ERP" value="/erp" icon={<BusinessCenterIcon />} />
          <BottomNavigationAction label="Más" value="more" icon={<MenuIcon />} />
        </BottomNavigation>
      </Paper>
      <MoreMenu open={moreMenuOpen} onClose={() => setMoreMenuOpen(false)} />
    </>
  );
};

export default BottomNav;
