import React from 'react';

function HomepageImage() {
  const url = 'https://cdn.dribbble.com/users/500242/screenshots/4198035/airbnb-wine-toast.gif';

  return (
    <img src={url} style={{width: 500}} alt='' />
  );
}

export default HomepageImage;