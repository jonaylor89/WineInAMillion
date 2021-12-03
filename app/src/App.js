import HomepageImage from './components/HomepageImage';
import SearchBox from './components/SearchBox';
import './App.css';

function App() {
  return (
    <div class="App">
      <header class="App-header">
        <h1>Wine in a Million</h1>
        <HomepageImage />
      </header>
      <div class="App-Component">
        <SearchBox />
      </div>
    </div>
  );
}

export default App;
