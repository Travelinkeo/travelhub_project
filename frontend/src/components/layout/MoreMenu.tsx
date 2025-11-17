'use client';

import React from 'react';
import { Dialog, DialogTitle, DialogContent, IconButton } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

interface MoreMenuProps {
  open: boolean;
  onClose: () => void;
}

const MoreMenu = ({ open, onClose }: MoreMenuProps) => {
  return (
    <Dialog fullScreen open={open} onClose={onClose}>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        Menú Principal
        <IconButton edge="end" color="inherit" onClick={onClose} aria-label="close">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <p>More menu content will be implemented here.</p>
        {/* We will add the rest of the navigation items and user actions here */}
      </DialogContent>
    </Dialog>
  );
};

export default MoreMenu;
